from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from langgraph.graph import StateGraph, END
import json
from openai import OpenAI
import os
from collections import defaultdict

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
    state_list = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
                  "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
                  "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
                  "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York",
                  "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
                  "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
                  "West Virginia", "Wisconsin", "Wyoming"]
    
    coverage_completion = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        messages=[
            {
                "role": "system", 
                "content": "Your Tasks: 1. Extract the list of states from the user-provided input. 2. Give response in array of strings format. 3. Give list of states only from this list:"+ str(state_list) +"4. Response should in json Format Like: {'data': ['Florida', 'Texas', 'Ohio'...}]"
            },
            {
                "role": "user",
                "content":str(required_coverage_area)
            }
        ]
    )

    required_states = json.loads(coverage_completion.choices[0].message.content)["data"]
    filtered_vendors = []

    for carrier in carrier_coverage_db:
        carrier_name = carrier['name']
        
        covered_states = set()
        
        for coverage in carrier['coverages']:
            state_name = coverage['state']
            coverage_percentage = coverage['coverage']

            if state_name in required_states and coverage_percentage > 0.75:
                covered_states.add(state_name)

        if set(required_states).issubset(covered_states):
            filtered_vendors.append(str(carrier_name))

    filtered_vendors = list(set(filtered_vendors))

    state.filtered_vendors = filtered_vendors
    return state

def evaluate_carrier_attributes(state: ShippingState) -> ShippingState:

   
    evaluated_vendors = []
    
    tracking_score_map = {
        "Advanced": 100,
        "Intermediate": 50,
        "Basic": 25
    }
    
    for carrier in state.filtered_vendors:
        for carrier_data in carrier_attributes_db:
            if carrier_data['name'] == carrier:
                # Calculate the average score based on the attributes
                onboarding_score = 100 / carrier_data["onboardingTime"]  # OnboardingTime score (higher is better if faster)
                tracking_capability_score = tracking_score_map.get(carrier_data["trackingCapabilities"], 0)  # Use the tracking score map
                sustainability_score = carrier_data["sustainabilityScore"]  # Sustainability score out of 100
                
                avg_score = (onboarding_score + tracking_capability_score + sustainability_score) / 3
                
                evaluated_vendors.append({carrier: round(avg_score, 2)})

    state.evaluated_vendors = evaluated_vendors

    return state

def analyze_max_weight(state: ShippingState) -> ShippingState:
    required_weight_range = state.requirements["weight_range_in_lbs"]
   
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "Give the maximum weight in based on user input. Response should be json format like {'data': 100}"},
            {
                "role": "user",
                "content": str(required_weight_range)
            }
        ]
    )
    max_required_weight=json.loads(completion.choices[0].message.content)["data"]
    print(max_required_weight)
    analyzed_vendors = []
    for carrier, max_weight in carrier_max_weight_db.items():
 
        if carrier not in state.filtered_vendors:
            continue

        if max_required_weight <= max_weight:
            score = 1.0  
        else:
            score = 0.0 
        analyzed_vendors.append({carrier: score})

    
    state.analyzed_vendors = analyzed_vendors
    return state

def assess_return_need(state: ShippingState) -> ShippingState:
    assessed_vendors = []
    for carrier in state.filtered_vendors:
        assessed_vendors.append({carrier: 1.0 if carrier_return_support_db.get(carrier) else 0.0})
    state.assessed_vendors = assessed_vendors
    
    return state

def rank_and_reason(state: ShippingState) -> ShippingState:
    requirements = str(state.requirements)
    evaluated_vendors = str(state.evaluated_vendors)
    analyzed_vendors = str(state.analyzed_vendors)
    assessed_vendors = str(state.assessed_vendors)
    
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        messages=[
            {
                "role": "system", 
                "content": f"""
                You are an expert assistant in shipping carrier recommendations. 
                You are provided with the user's shipping requirements and a breakdown of how different carriers rate across multiple criteria.
                
                Your task is:
                1. Based on the data provided, rank the top 4 carriers.
                2. Provide a 2-3 sentence explanation for each recommendation, focusing on why the carrier is a good fit based on the user's needs and the data.

                The data available is as follows:
                - User's requirements: {requirements}
                - Carrier evaluations (scores based on carrier attributes): {evaluated_vendors} 
                - Weight range analysis (scores based on ability to handle the required package weight): {analyzed_vendors} 
                - Return support assessment (whether the carrier supports return shipments): {assessed_vendors} 

                Output the response in the following JSON format:
                {{
                    'data': [
                        {{'first_ranked_carrier': 'carrier_name', 'explanation': 'explanation_text'}},
                        {{'second_ranked_carrier': 'carrier_name', 'explanation': 'explanation_text'}},
                        {{'third_ranked_carrier': 'carrier_name', 'explanation': 'explanation_text'}},
                        {{'fourth_ranked_carrier': 'carrier_name', 'explanation': 'explanation_text'}}
                    ]
                }}

                Avoid using the phrase "carrier attributes" and focus on practical reasons for the rankings.
                """
            },
            {
                "role": "user",
                "content": "Give response in JSON"
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
    return {"status": "API is running"}
