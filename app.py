import json

import openai
import streamlit as st
from loguru import logger

from utils import CONFIG
from utils.functions import calculate, create_lead, openai_functions, retrieve_profile


def app():
    st.set_page_config(page_title="Sales Copilot", page_icon="🤝")
    st.title("🤝 Sales Copilot")
    """
    Extract information from LinkedIn profile, insert it into a Close CRM and recieve a 1-liner icebreaker
    """
    if "messages" not in st.session_state:
        intro = "👋 Hi! I'm a sales assistant. I can help you with filling out your CRM, finding information about your leads, and writing icebreakers."
        intro += "\nYou might begin with inserting a LinkedIn profile URL along with company which you are interested in, and I'll try to extract information from it."
        st.session_state["messages"] = [
            {
                "role": "system",
                "content": "Given a LinkedIn profile URL and a company, you should retrieve information about the person, the company and fill as many CRM fields as possible. After it, you should come with 1-liner ice breaker. Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous.",
            },
            {"role": "assistant", "content": intro},
        ]

    for msg in st.session_state.messages[1:]:
        with st.chat_message(msg["role"]):
            for fn in msg.get("fn_calls", []):
                with st.status(f"""Executing `{fn["name"]}`""", state=fn["state"]):
                    st.code(fn["arguments"], language="json")
                    st.write(fn["results"])
            st.write(msg["content"])

    if prompt := st.chat_input():
        # request_id = log_request(query=prompt, messages=st.session_state.messages)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        with st.chat_message("assistant"):
            response_object = {"role": "assistant", "fn_calls": []}
            response = ""
            status_space = st.container()
            resp_container = st.empty()
            # Loop to support function calls and subsequent generations by OpenAI
            for i in range(int(CONFIG["ml"]["max_function_calls"])):
                func_name = ""
                # We store function calls in a slightly different format than the one expected by OpenAI - convert it here
                openai_funcs = []
                for fn in response_object["fn_calls"]:
                    openai_funcs.extend(
                        [
                            {
                                "role": "assistant",
                                "content": None,
                                "function_call": {"name": fn["name"], "arguments": fn["arguments"]},
                            },
                            {
                                "role": "function",
                                "name": fn["name"],
                                "content": str(fn["results"]),
                            },
                        ]
                    )

                msg_history = [
                    {
                        "role": msg["role"],
                        "content": (
                            f"I executed function to retrieve the result: {msg['fn_calls']}\n"
                            if "fn_calls" in msg
                            else ""
                        )
                        + msg["content"],
                    }
                    for msg in st.session_state.messages
                ]

                # Use deltas to stream back response
                for delta in openai.ChatCompletion.create(
                    model=CONFIG["ml"]["completions_model"],
                    messages=msg_history + openai_funcs,
                    functions=openai_functions,
                    function_call="auto",
                    stream=True,
                    temperature=float(CONFIG["ml"]["temperature"]),
                ):
                    if content := delta.choices[0].delta.get("content", ""):
                        response += content
                        resp_container.markdown(response)
                    if fn := delta.choices[0].delta.get("function_call", ""):
                        if "name" in fn:  # Only returned once at the beginning currently
                            func_name = fn.get("name")
                            func_args = ""
                            status = status_space.status(f"Executing `{func_name}`")
                            args_container = status.empty()
                        if arg_delta := fn.get("arguments", ""):
                            func_args += arg_delta
                            args_container.code(func_args, language="json")

                # Run the web search if requested and append the result for the next loop iteration
                if func_name:
                    if func_name == "retrieve_profile":
                        url = json.loads(func_args).get("url", "")
                        profile_type = json.loads(func_args).get("profile_type", "")
                        if not url or not profile_type:
                            st.error("LLM tried to search without url or profile type")
                            st.stop()
                        profile = retrieve_profile(url=url, profile_type=profile_type)
                        results = profile.dict()
                    elif func_name == "create_lead":
                        # "company_name",
                        # "company_url",
                        # "company_slogan",
                        # "company_city",
                        # "company_state",
                        # "company_country",
                        # "person_name",
                        # "person_title",
                        # "person_url",
                        company_name = json.loads(func_args).get("company_name", "")
                        company_url = json.loads(func_args).get("company_url", "")
                        company_slogan = json.loads(func_args).get("company_slogan", "")
                        company_city = json.loads(func_args).get("company_city", "")
                        company_state = json.loads(func_args).get("company_state", "")
                        company_country = json.loads(func_args).get("company_country", "")
                        person_name = json.loads(func_args).get("person_name", "")
                        person_title = json.loads(func_args).get("person_title", "")
                        person_url = json.loads(func_args).get("person_url", "")
                        if (
                            not company_name
                            or not company_url
                            or not company_slogan
                            or not company_city
                            or not company_state
                            or not company_country
                            or not person_name
                            or not person_title
                            or not person_url
                        ):
                            st.error("LLM tried to create a lead without all required fields")
                            st.stop()
                        lead = create_lead(
                            company_name=company_name,
                            company_url=company_url,
                            company_slogan=company_slogan,
                            company_city=company_city,
                            company_state=company_state,
                            company_country=company_country,
                            person_name=person_name,
                            person_title=person_title,
                            person_url=person_url,
                        )
                        results = lead
                    elif func_name == "calculate":
                        s = json.loads(func_args).get("s", "")
                        if not s:
                            st.error("LLM tried to calculate without a string")
                            st.stop()
                        results = calculate(s=s)
                    else:
                        st.error(f"LLM tried to call unknown function: {func_name}")
                        st.stop()
                    status.write(results)
                    status.update(state="complete")
                    response_object["fn_calls"].append(
                        {
                            "name": func_name,
                            "arguments": func_args,
                            "results": results,
                            "state": "complete",
                        }
                    )
                elif response:
                    # Stop once the LLM generates an actual response
                    response_object["content"] = response
                    st.session_state.messages.append(response_object)
                    # update_log(request_id=request_id, response_object=response_object)
                    break
                else:
                    st.error("Unexpected response from LLM")
                    st.stop()
            if st.session_state.messages[-1]["role"] != "assistant":
                st.error("Something went wrong: reached max iteration of function calls.")


if __name__ == "__main__":
    app()
