from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from langgraph.graph import StateGraph, END
import json
from openai import OpenAI
import os
# Load your data files (update the paths to your actual files)
with open("orchestro.carriercoverages.json") as carrier_coverage:
    carrier_coverage_db = json.load(carrier_coverage)

with open("orchestro.carrierinteractives.json") as carrier_attributes:
    carrier_attributes_db = json.load(carrier_attributes)

with open("orchestro.carriermaxweight.json") as carrier_max_weight:
    carrier_max_weight_db = json.load(carrier_max_weight)

with open("orchestro.carrierreturnssupport.json") as carrier_return_support:
    carrier_return_support_db = json.load(carrier_return_support)
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)
# Define the Pydantic model for incoming requests
class ShippingRequirements(BaseModel):
    coverage_area: List[str]
    carrier_attributes: Dict[str, str]
    weight_range_in_lbs: str
    return_needed: str

# Define the state structure using TypedDict or BaseModel
class ShippingState(BaseModel):
    requirements: dict
    filtered_vendors: List[str]
    evaluated_vendors: List[dict]
    analyzed_vendors: List[dict]
    assessed_vendors: List[dict]
    ranked_vendors: List[dict]

# Define the logic for the graph nodes
def collect_requirements(state: ShippingState) -> ShippingState:
    return state

def filter_vendors(state: ShippingState) -> ShippingState:
    required_coverage_area = state.requirements["coverage_area"]
    
    coverage_completion = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You are an assistant that is an expert in shipping carrier coverage. You are given the following data about shipping carrier coverage:" + str(carrier_coverage_db)},
            {
                "role": "user",
                "content": "I'm a shipper and I want to ship to the following destinations:" + str(required_coverage_area) + ". Please provide a list of the top 15 carriers that ship to these destinations and return a JSON in this format {'data': ['UPS', 'FedEx', 'Orchestro'...}]"
            }
        ]
    )
    state.filtered_vendors = json.loads(coverage_completion.choices[0].message.content)["data"]
    
    # Filter out vendors not supporting returns
    state.filtered_vendors = [carrier for carrier in state.filtered_vendors if carrier in carrier_return_support_db]
    return state

def evaluate_carrier_attributes(state: ShippingState) -> ShippingState:
    required_carrier_attributes = state.requirements["carrier_attributes"]
    
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You are an assistant that is an expert in shipping carrier attributes. You are given the following data about shipping carrier attributes:" + str(carrier_attributes_db)},
            {
                "role": "user",
                "content": "I'm a shipper and I have the following shipping needs:" + str(required_carrier_attributes) + ". Please rate each of these carriers: " +str(state.filtered_vendors)+ " based on whether they support my tracking needs and return a JSON in this format {'data': [{'UPS':0.9}, {'FedEx':0.8}, {'Orchestro':0.9}...}]"
            }
        ]
    )
    
    state.evaluated_vendors = json.loads(completion.choices[0].message.content)["data"]
    
    return state

def analyze_max_weight(state: ShippingState) -> ShippingState:
    required_weight_range = state.requirements["weight_range_in_lbs"]
    
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You are an assistant that is an expert in the weight ranges that shipping carriers permit. You are given the following data about the max weight in lbs that shipping carriers support:" + str(carrier_max_weight_db)},
            {
                "role": "user",
                "content": "I'm a shipper and I plan to ship packages that weigh in the following range:" + str(required_weight_range) + ". If a carrier supports the entire weight range that I wish to ship then give them a score of 1.0, if only a part then give them a lower score. Please rate each of these carriers: " +str(state.filtered_vendors)+ " based on whether they support my weight range and return a JSON in this format {'data': [{'UPS':0.9}, {'FedEx':0.8}, {'Orchestro':0.9}...}]"
            }
        ]
    )
    
    state.analyzed_vendors = json.loads(completion.choices[0].message.content)["data"]
    
    return state

def assess_return_need(state: ShippingState) -> ShippingState:
    assessed_vendors = []
    for carrier in state.filtered_vendors:
        assessed_vendors.append({carrier: 1.0 if carrier_return_support_db.get(carrier) else 0.0})
    state.assessed_vendors = assessed_vendors
    
    return state

def rank_and_reason(state: ShippingState) -> ShippingState:
    
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You are an assistant that is an expert in recommending shipping carriers. You are given the following data about the user's requirements  "+ str(state.requirements) + " you have determined that in terms of carrier attributes required by the user this is how the different carriers rate" + str(state.evaluated_vendors) + ". In terms of supporting the desired package shipping weight ranges this is how the different carriers rate:  "+str(state.analyzed_vendors)+". And in terms of providing return functionality, these are the carriers that provide it: "+ str(state.assessed_vendors)},
            {
                "role": "user",
                "content": "Please rank the top 4 carriers you'd recommend with 2-3 sentence explaination on why so and output the info in the following JSON format: {'data': [{'first_ranked_carrier': 'carrier_name', 'explanation': 'explaination_text'}, {'second_ranked_carrier': 'carrier_name', 'explanation': 'explaination_text'}, {'third_ranked_carrier': 'carrier_name', 'explanation': 'explaination_text'}, {'fourth_ranked_carrier': 'carrier_name', 'explanation': 'explaination_text'}]}. Don't mention the phrase carrier attributes."
            }
        ]
    )
    
    state.ranked_vendors = json.loads(completion.choices[0].message.content)["data"]
    
    return state

# Create the graph
workflow = StateGraph(ShippingState)
workflow.add_node("Collect Requirements", collect_requirements)
workflow.add_node("Filter Vendors", filter_vendors)
workflow.add_node("Evaluate Carrier Attributes", evaluate_carrier_attributes)
workflow.add_node("Analyze Max Weight", analyze_max_weight)
workflow.add_node("Returns Needed", assess_return_need)
workflow.add_node("Rank & Reason", rank_and_reason)

workflow.set_entry_point("Collect Requirements")
workflow.add_edge("Collect Requirements", "Filter Vendors")
workflow.add_edge("Filter Vendors", "Evaluate Carrier Attributes")
workflow.add_edge("Evaluate Carrier Attributes", "Analyze Max Weight")
workflow.add_edge("Analyze Max Weight", "Returns Needed")
workflow.add_edge("Returns Needed", "Rank & Reason")
workflow.add_edge("Rank & Reason", END)

# API route to process shipping request
@app.post("/process-shipping/")
async def process_shipping_requirements(req: ShippingRequirements):
    initial_state = ShippingState(
        requirements=req.dict(),
        filtered_vendors=[],
        evaluated_vendors=[],
        analyzed_vendors=[],
        assessed_vendors=[],
        ranked_vendors=[]
    )
    
    final_state = workflow.compile().invoke(initial_state)
    
    
    return {
    "coverage_area_filtered_vendors": final_state['filtered_vendors'],
    "carrier_attributes_evaluated_vendors": final_state['evaluated_vendors'],
    "weight_range_in_lbs_analyzed_vendors_": final_state['analyzed_vendors'],
    "return_needed_assessed_vendors": final_state['assessed_vendors'],
    "ranked_vendors": final_state['ranked_vendors']
}


@app.get("/")
async def healthcheck():
    return {"status": "ok"}
