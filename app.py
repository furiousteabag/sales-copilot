import json
from pprint import pformat, pprint

import openai
import streamlit as st
from loguru import logger

from utils import CONFIG
from utils.functions import calculate, create_lead, openai_functions, retrieve_profile


def app():
    st.set_page_config(page_title="Sales Copilot", page_icon="🤝")
    st.title("🤝 Sales Copilot")
    """
    Extract information from LinkedIn profile, insert it into a Close CRM and recieve a message to send to the person.
    """
    user_name = st.sidebar.text_input("Your name:", value="Alex")
    user_title = st.sidebar.text_input("Title:", value="Co-Founder & CEO")
    user_company = st.sidebar.text_input("Enter your company:", value="AskGuru")
    user_company_description = st.sidebar.text_area(
        "Company description:",
        value="AskGuru is a human-supervised conversational AI in the form of a chatbot to generate leads for website owners because unengaging, slow, and irrelevant chatbot replies reduce # of visitors making the CTA by up to 50%.",
        height=100,
    )
    # short_message_example = st.sidebar.text_area(
    #     "Enter short message example 👇",
    #     value="Hi Wisnu, I'm Alex from AskGuru. We've crafted a copilot for support agents, streamlining instant reply suggestions. Your work at Kata.ai, especially in Conversational AI, truly stands out. Could we have a ~20-minute chat to discuss your perspective on tech and management?",
    #     height=230,
    # )
    # long_message_example = st.sidebar.text_area(
    #     "Enter long message example 👇",
    #     value="Hi Irzan, I'm Alex!\n\nI’ve recently developed a tool aimed at enhancing support agent efficiency by providing them with quick, relevant replies. Your vision and commitment to making people's lives easier through technology, especially with the impressive work you've done at Kata.ai, resonates deeply with me. I genuinely believe that the fusion of technology and human touch can make a huge difference.\n\nI'm keen to understand and gain insights from your journey as the CEO and Co-Founder of Kata.ai, especially in the Conversational AI landscape. I’m sure your perspective on the future of tech, and how brands can deeply connect with their audience, would be invaluable to our development.\n\nWould you be open to a ~20-minute chat to dive deeper into this?",
    #     height=500,
    # )

    if not user_name or not user_title or not user_company or not user_company_description:
        st.warning("Please fill out your name, title, company and company description.")
        return
    if "messages" not in st.session_state:
        intro = "👋 Hi! I'm a sales assistant. Here is a list of things I can do for you:\n"
        intro += "\n".join([f"- {f['description']}" for f in openai_functions])
        # intro += "\n\nYou might begin with inserting a LinkedIn profile URL along with company which you are interested in, and I'll try to extract information from it."
        intro += "\n\nYou may begin with something like:\n```\nretrieve necessary info and create lead for https://www.linkedin.com/in/chrislohy/ for neocortex\n```\n"
        intro += "And follow up with:\n```\nwrite a personalized LinkedIn InMail\n```\n"
        st.session_state["messages"] = [
            {
                "role": "system",
                # "content": "Ask for clarification if a user request is ambiguous. Given a LinkedIn profile URL and a company, you should retrieve information about the person, the company and fill as many CRM fields as possible. After it, you should come with a long or short personalized cold message. Don't make assumptions about what values to plug into functions.",
                "content": "Ask for clarification if a user request is ambiguous. Don't make assumptions about what values to plug into functions. Execute functions if you can extract necessary values. Before creating company profile make sure you have made a separate request to retrieve company info.",
            },
            {"role": "assistant", "content": intro},
        ]

    # example_messages = ""
    # if short_message_example:
    #     example_messages += f"Short message example:\n```\n{short_message_example}\n```\n\n"
    # if long_message_example:
    #     example_messages += f"Long message example:\n```\n{long_message_example}\n```"

    # if st.session_state.messages[1]["content"] != example_messages:
    #     if "message example" in st.session_state.messages[1]["content"]:
    #         st.session_state.messages[1]["content"] = example_messages
    #     else:
    #         st.session_state.messages.insert(1, {"role": "user", "content": example_messages})

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

                # msg_history = [
                #     {
                #         "role": msg["role"],
                #         "content": (
                #             f"I executed function to retrieve the result: {msg['fn_calls']}\n"
                #             if "fn_calls" in msg
                #             else ""
                #         )
                #         + msg["content"],
                #     }
                #     for msg in st.session_state.messages
                # ]
                # msg_history = [
                #     item
                #     for msg in st.session_state.messages
                #     for item in [
                #         {
                #             "role": msg["role"],
                #             "content": f"I executed function to retrieve the result: {msg['fn_calls']}\n"
                #             if "fn_calls" in msg
                #             else None,
                #         },
                #         {"role": msg["role"], "content": msg["content"]},
                #     ]
                #     if item["content"]
                # ]
                msg_history, fn_calls_prefix = [], ""
                for msg in st.session_state.messages:
                    msg_history.append(
                        {
                            "role": msg["role"],
                            "content": msg["content"],
                        }
                    )
                    if msg["role"] == "user":
                        last_user_msg_idx = len(msg_history) - 1
                    fn_calls_prefix += (
                        ("\n".join([f"{fn['name']}: {fn['results']}" for fn in msg["fn_calls"]]) + "\n")
                        if "fn_calls" in msg
                        else ""
                    )

                if fn_calls_prefix:
                    msg_history[last_user_msg_idx]["content"] = (
                        f"Use the following information withing your answer from previous function calls if you will find it useful:\n```\n{fn_calls_prefix}```\n\n"
                        + msg_history[last_user_msg_idx]["content"]
                    )

                msg_history[last_user_msg_idx]["content"] = (
                    f"If required: here is a data about me (e.g. for crafting personalized messages):\n```\nname: {user_name}\ntitle: {user_title}\ncompany: {user_company}\ncompany description: {user_company_description}\n```\n\n"
                    + msg_history[last_user_msg_idx]["content"]
                )

                logger.info(f"msg_history: {pformat(msg_history + openai_funcs)}")
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
                            or not company_country
                            or not person_name
                            or not person_url
                        ):
                            st.error(f"LLM tried to create a lead without all required fields. Got: {func_args}")
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
