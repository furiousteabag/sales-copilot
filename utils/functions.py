import json
import os
from time import sleep
from typing import Dict, List

import requests
from loguru import logger

from utils import CONFIG
from utils.schemas import CompanyProfile, PersonProfile, ProfileType


def calculate(s: str) -> float:
    return eval(s)


calculate.openai_representation = {
    "name": "calculate",
    "description": "Calculate the result of a mathematical expression. Useful for calculating the total price of a shopping cart.",
    "parameters": {
        "type": "object",
        "properties": {
            "s": {
                "type": "string",
                "description": "The mathematical expression to be evaluated. It is a string that will be evaluated using Python's `eval` function.",
            }
        },
        "required": ["s"],
    },
}


def retrieve_profile(url: str, profile_type: ProfileType) -> PersonProfile | CompanyProfile:
    logger.info(f"Retrieving profile for {url}")

    scraper = "linkedinProfile" if profile_type == "person" else "linkedinCompanyProfile"
    apiEndPoint = "http://api.scraping-bot.io/scrape/data-scraper"
    apiEndPointResponse = "http://api.scraping-bot.io/scrape/data-scraper-response?"
    payload = json.dumps({"url": url, "scraper": scraper})
    headers = {"Content-Type": "application/json"}
    auth = (os.environ["SCRAPINGBOT_USERNAME"], os.environ["SCRAPINGBOT_API_KEY"])

    response = requests.request("POST", apiEndPoint, data=payload, auth=auth, headers=headers)
    if response.status_code != 200:
        logger.info(response.text)
        return None

    responseId = response.json()["responseId"]
    pending = True
    while pending:
        # sleep 5s between each loop, social-media scraping can take quite long to complete
        # so there is no point calling the api quickly as we will return an error if you do so
        sleep(5)
        finalResponse = requests.request(
            "GET", apiEndPointResponse + "scraper=" + scraper + "&responseId=" + responseId, auth=auth
        )
        result = finalResponse.json()
        if type(result) is list:
            pending = False
            # logger.info(result[0])
            profile = PersonProfile(**result[0]) if profile_type == "person" else CompanyProfile(**result[0])
        elif type(result) is dict:
            if "status" in result and result["status"] == "pending":
                logger.info(result["message"] + " " + url)
                continue
            elif result["error"] is not None:
                pending = False
                logger.error(json.dumps(result, indent=4))
    return profile


retrieve_profile.openai_representation = {
    "name": "retrieve_profile",
    "description": "Retrieve a profile from LinkedIn.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The url of the profile to be retrieved from LinkedIn.",
            },
            "profile_type": {
                "type": "string",
                "enum": ["person", "company"],
            },
        },
        "required": ["url", "profile_type"],
    },
}


def create_lead(
    company_name: str,
    company_url: str,
    company_slogan: str,
    company_city: str,
    company_country: str,
    person_name: str,
    person_url: str,
    company_state: str = "",
    person_title: str = "",
) -> Dict:
    auth = (os.environ["CLOSECRM_API_KEY"], "")
    payload = json.dumps(
        {
            "name": company_name,
            "url": company_url,
            "description": company_slogan,
            "status_id": "stat_RwOjavEVGcZ179xledpACAJFNnIPdciHeKdAkpCJu6v",
            "addresses": [
                {
                    "label": "business",
                    "city": company_city,
                    "state": company_state,
                    "country": company_country,
                }
            ],
            "contacts": [
                {
                    "name": person_name,
                    "title": person_title,
                    "urls": [
                        {
                            "type": "url",
                            "url": person_url,
                        }
                    ],
                }
            ],
        }
    )
    headers = {"Content-Type": "application/json"}

    response = requests.request("POST", "https://api.close.com/api/v1/lead/", data=payload, auth=auth, headers=headers)
    if response.status_code != 200:
        logger.error(response.text)
        return None

    return {"lead_url": response.json()["html_url"], "lead_id": response.json()["id"]}


create_lead.openai_representation = {
    "name": "create_lead",
    "description": "Create a lead in Close CRM.",
    "parameters": {
        "type": "object",
        "properties": {
            "company_name": {
                "type": "string",
                "description": "The name of the company.",
            },
            "company_url": {
                "type": "string",
                "description": "The url of the company.",
            },
            "company_slogan": {
                "type": "string",
                "description": "The slogan of the company.",
            },
            "company_city": {
                "type": "string",
                "description": "The city of the company.",
            },
            "company_state": {
                "type": "string",
                "description": "The state of the company.",
            },
            "company_country": {
                "type": "string",
                "description": "The country of the company.",
            },
            "person_name": {
                "type": "string",
                "description": "The name of the person.",
            },
            "person_title": {
                "type": "string",
                "description": "The title of the person.",
            },
            "person_url": {
                "type": "string",
                "description": "The url of the person.",
            },
        },
        "required": [
            "company_name",
            "company_url",
            "company_slogan",
            "company_city",
            "company_country",
            "person_name",
            "person_url",
        ],
    },
}


openai_functions = [
    retrieve_profile.openai_representation,
    create_lead.openai_representation,
    calculate.openai_representation,
]
