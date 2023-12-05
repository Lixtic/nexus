from typing import Any, Callable, List, Tuple

import huggingface_hub

from dataclasses import dataclass

from datetime import datetime

from time import sleep

import inspect

from random import randint

from urllib.parse import quote

from black import Mode, format_str

import gradio as gr

from huggingface_hub import InferenceClient

from constants import *
from config import DemoConfig
from tools import Tools


@dataclass
class Function:
    name: str
    short_description: str
    description_function: Callable[[Any], str]
    explanation_function: Callable[[Any], str]


FUNCTIONS = [
    Function(
        name="get_current_location",
        short_description="Finding your city",
        description_function=lambda *_, **__: "Finding your city",
        explanation_function=lambda result: f"Found you in {result}!",
    ),
    Function(
        name="sort_results",
        short_description="Sorting results",
        description_function=lambda places, sort, descending=True, first_n=None: f"Sorting results by {sort} from "
        + ("lowest to highest" if not descending else "highest to lowest"),
        explanation_function=lambda result: "Done!",
    ),
    Function(
        name="get_latitude_longitude",
        short_description="Convert to coordinates",
        description_function=lambda location: f"Converting {location} into latitude and longitude coordinates",
        explanation_function=lambda result: "Converted!",
    ),
    Function(
        name="get_distance",
        short_description="Calcuate distance",
        description_function=lambda place_1, place_2: "Calculating distances",
        explanation_function=lambda result: result[2],
    ),
    Function(
        name="get_recommendations",
        short_description="Read recommendations",
        description_function=lambda topics, **__: f"Reading recommendations for the following "
        + (
            f"topics: {', '.join(topics)}" if len(topics) > 1 else f"topic: {topics[0]}"
        ),
        explanation_function=lambda result: f"Read {len(result)} recommendations",
    ),
    Function(
        name="find_places_near_location",
        short_description="Look for places",
        description_function=lambda type_of_place, location, radius_miles=50: f"Looking for places near {location} within {radius_miles} with the following "
        + (
            f"types: {', '.join(type_of_place)}"
            if isinstance(type_of_place, list)
            else f"type: {type_of_place}"
        ),
        explanation_function=lambda result: f"Found "
        + (f"{len(result)} places!" if len(result) > 1 else f"1 place!"),
    ),
    Function(
        name="get_some_reviews",
        short_description="Fetching reviews",
        description_function=lambda place_names, **_: f"Fetching reviews for the requested items",
        explanation_function=lambda result: f"Fetched {len(result)} reviews!",
    ),
]


class FunctionsHelper:
    FUNCTION_DEFINITION_TEMPLATE = '''Function:
def {name}{signature}:
"""
{docstring}
"""

'''
    PROMPT_TEMPLATE = """{function_definitions}User Query: {query}<human_end>Call:"""

    def __init__(self, tools: Tools) -> None:
        self.tools = tools

        function_definitions = ""
        for function in FUNCTIONS:
            f = getattr(tools, function.name)
            signature = inspect.signature(f)
            docstring = inspect.getdoc(f)

            function_str = self.FUNCTION_DEFINITION_TEMPLATE.format(
                name=function.name, signature=signature, docstring=docstring
            )
            function_definitions += function_str

        self.prompt_without_query = self.PROMPT_TEMPLATE.format(
            function_definitions=function_definitions, query="{query}"
        )

    def get_prompt(self, query: str):
        return self.prompt_without_query.format(query=query)

    def get_function_call_plan(self, function_call_str: str) -> List[str]:
        function_call_list = []
        locals_to_pass = {"function_call_list": function_call_list}
        for f in FUNCTIONS:
            name = f.name
            exec(
                f"def {name}(**_):\n\tfunction_call_list.append('{f.short_description}')",
                locals_to_pass,
            )
        calls = [c.strip() for c in function_call_str.split(";") if c.strip()]
        [eval(call, locals_to_pass) for call in calls]
        return function_call_list

    def run_function_call(self, function_call_str: str):
        function_call_list = []
        locals_to_pass = {"function_call_list": function_call_list, "tools": self.tools}
        for f in FUNCTIONS:
            name = f.name

            locals_to_pass[f"{name}_description_function"] = f.description_function
            locals_to_pass[f"{name}_explanation_function"] = f.explanation_function

            function_definition = f"""
def {name}(**kwargs):
    result = tools.{f.name}(**kwargs)
    function_call_list.append(({name}_description_function(**kwargs), {name}_explanation_function(result)))
    return result
"""
            exec(function_definition, locals_to_pass)

        calls = [c.strip() for c in function_call_str.split(";") if c.strip()]
        for call in calls:
            locals_to_pass["function_call_list"] = function_call_list = []
            result = eval(call, locals_to_pass)
            yield result, function_call_list


class RavenDemo(gr.Blocks):
    def __init__(self, config: DemoConfig) -> None:
        theme = gr.themes.Soft(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.blue,
        )
        super().__init__(theme=theme, css=CSS, title="NexusRaven V2 Demo")

        self.config = config
        self.tools = Tools(config)
        self.functions_helper = FunctionsHelper(self.tools)

        self.raven_client = InferenceClient(
            model=config.raven_endpoint, token=config.hf_token
        )
        self.summary_model_client = InferenceClient(config.summary_model_endpoint)

        self.max_num_steps = 20

        with self:
            gr.HTML(HEADER_HTML)
            with gr.Row():
                gr.Image(
                    "NexusRaven.png",
                    show_label=False,
                    show_share_button=True,
                    min_width=200,
                    scale=1,
                )
                with gr.Column(scale=4, min_width=800):
                    gr.Markdown(INTRO_TEXT, elem_classes="inner-large-font")
                    with gr.Row():
                        examples = [
                            gr.Button(query_name) for query_name in EXAMPLE_QUERIES
                        ]

            user_input = gr.Textbox(
                placeholder="Ask me anything!",
                show_label=False,
                autofocus=True,
            )

            raven_function_call = gr.Code(
                label="🐦‍⬛ NexusRaven V2 13B zero-shot generated function call",
                language="python",
                interactive=False,
                lines=10,
            )
            with gr.Accordion(
                "Executing plan generated by 🐦‍⬛ NexusRaven V2 13B", open=True
            ) as steps_accordion:
                steps = [
                    gr.Textbox(visible=False, show_label=False)
                    for _ in range(self.max_num_steps)
                ]

            with gr.Column():
                initial_relevant_places = self.get_relevant_places([])
                relevant_places = gr.State(initial_relevant_places)
                place_dropdown_choices = self.get_place_dropdown_choices(
                    initial_relevant_places
                )
                places_dropdown = gr.Dropdown(
                    choices=place_dropdown_choices,
                    value=place_dropdown_choices[0],
                    label="Relevant places",
                )
                gmaps_html = gr.HTML(self.get_gmaps_html(initial_relevant_places[0]))

            summary_model_summary = gr.Textbox(
                label="Chat summary",
                interactive=False,
                show_copy_button=True,
                lines=10,
                max_lines=1000,
                autoscroll=False,
                elem_classes="inner-large-font",
            )

            with gr.Accordion("Raven inputs", open=False):
                gr.Textbox(
                    label="Available functions",
                    value="`" + "`, `".join(f.name for f in FUNCTIONS) + "`",
                    interactive=False,
                    show_copy_button=True,
                )
                gr.Textbox(
                    label="Raven prompt",
                    value=self.functions_helper.get_prompt("{query}"),
                    interactive=False,
                    show_copy_button=True,
                    lines=20,
                )

            user_input.submit(
                fn=self.on_submit,
                inputs=[user_input],
                outputs=[
                    user_input,
                    raven_function_call,
                    summary_model_summary,
                    relevant_places,
                    places_dropdown,
                    gmaps_html,
                    steps_accordion,
                    *steps,
                ],
                concurrency_limit=20,  # not a hyperparameter
                api_name=False,
            )

            for i, button in enumerate(examples):
                button.click(
                    fn=EXAMPLE_QUERIES.get,
                    inputs=button,
                    outputs=user_input,
                    api_name=f"button_click_{i}",
                )

            places_dropdown.input(
                fn=self.get_gmaps_html_from_dropdown,
                inputs=[places_dropdown, relevant_places],
                outputs=gmaps_html,
            )

    def on_submit(self, query: str, request: gr.Request):
        def get_returns():
            return (
                user_input,
                raven_function_call,
                summary_model_summary,
                relevant_places,
                places_dropdown,
                gmaps_html,
                steps_accordion,
                *steps,
            )

        user_input = gr.Textbox(interactive=False)
        raven_function_call = ""
        summary_model_summary = ""
        relevant_places = []
        places_dropdown = ""
        gmaps_html = ""
        steps_accordion = gr.Accordion(open=True)
        steps = [gr.Textbox(value="", visible=False) for _ in range(self.max_num_steps)]
        yield get_returns()

        raven_prompt = self.functions_helper.get_prompt(
            query.replace("'", r"\'").replace('"', r"\"")
        )
        print(f"{'-' * 80}\nPrompt sent to Raven\n\n{raven_prompt}\n\n{'-' * 80}\n")
        stream = self.raven_client.text_generation(
            raven_prompt, **RAVEN_GENERATION_KWARGS
        )
        for s in stream:
            for c in s:
                raven_function_call += c
                raven_function_call = raven_function_call.removesuffix("<bot_end>")
                yield get_returns()

        print(f"Raw Raven response before formatting: {raven_function_call}")

        r_calls = [c.strip() for c in raven_function_call.split(";") if c.strip()]
        f_r_calls = []
        for r_c in r_calls:
            f_r_call = format_str(r_c.strip(), mode=Mode())
            f_r_calls.append(f_r_call)

        raven_function_call = "; ".join(f_r_calls)

        yield get_returns()

        self._set_client_ip(request)
        function_call_plan = self.functions_helper.get_function_call_plan(
            raven_function_call
        )
        for i, v in enumerate(function_call_plan):
            steps[i] = gr.Textbox(value=f"{i+1}. {v}", visible=True)
            yield get_returns()
            sleep(0.1)

        results_gen = self.functions_helper.run_function_call(raven_function_call)
        results = []
        previous_num_calls = 0
        for result, function_call_list in results_gen:
            results.extend(result)
            for i, (description, explanation) in enumerate(function_call_list):
                i = i + previous_num_calls

                if len(description) > 100:
                    description = function_call_plan[i]
                to_stream = f"{i+1}. {description} ..."
                steps[i] = ""
                for c in to_stream:
                    steps[i] += c
                    sleep(0.005)
                    yield get_returns()

                to_stream = "." * randint(0, 5)
                for c in to_stream:
                    steps[i] += c
                    sleep(0.2)
                    yield get_returns()

                to_stream = f" {explanation}"
                for c in to_stream:
                    steps[i] += c
                    sleep(0.005)
                    yield get_returns()

            previous_num_calls += len(function_call_list)

        relevant_places = self.get_relevant_places(results)
        gmaps_html = self.get_gmaps_html(relevant_places[0])
        places_dropdown_choices = self.get_place_dropdown_choices(relevant_places)
        places_dropdown = gr.Dropdown(
            choices=places_dropdown_choices, value=places_dropdown_choices[0]
        )
        steps_accordion = gr.Accordion(open=False)
        yield get_returns()

        while True:
            try:
                summary_model_prompt = self.get_summary_model_prompt(results, query)
                print(
                    f"{'-' * 80}\nPrompt sent to summary model\n\n{summary_model_prompt}\n\n{'-' * 80}\n"
                )
                stream = self.summary_model_client.text_generation(
                    summary_model_prompt, **SUMMARY_MODEL_GENERATION_KWARGS
                )
                for s in stream:
                    s = s.removesuffix("<|end_of_turn|>")
                    for c in s:
                        summary_model_summary += c
                        summary_model_summary = (
                            summary_model_summary.lstrip().removesuffix(
                                "<|end_of_turn|>"
                            )
                        )
                        yield get_returns()
            except huggingface_hub.inference._text_generation.ValidationError:
                if len(results) > 1:
                    new_length = (3 * len(results)) // 4
                    results = results[:new_length]
                    continue
                else:
                    break

            break

        user_input = gr.Textbox(interactive=True, autofocus=False)
        yield get_returns()

    def get_summary_model_prompt(self, results: List, query: str) -> None:
        # TODO check what outputs are returned and return them properly
        ALLOWED_KEYS = [
            "author_name",
            "text",
            "for_location",
            "time",
            "author_url",
            "language",
            "original_language",
            "name",
            "opening_hours",
            "rating",
            "user_ratings_total",
            "vicinity",
            "distance",
            "formatted_address",
            "price_level",
            "types",
        ]
        ALLOWED_KEYS = set(ALLOWED_KEYS)

        results_str = ""
        for idx, res in enumerate(results):
            if isinstance(res, str):
                results_str += f"{res}\n"
                continue

            assert isinstance(res, dict)

            item_str = ""
            for key, value in res.items():
                if key not in ALLOWED_KEYS:
                    continue

                key = key.replace("_", " ").capitalize()
                item_str += f"\t{key}: {value}\n"

            results_str += f"Result {idx + 1}\n{item_str}\n"

        current_time = datetime.now().strftime("%b %d, %Y %H:%M:%S")
        current_location = self.tools.get_current_location()

        prompt = SUMMARY_MODEL_PROMPT.format(
            current_location=current_location,
            current_time=current_time,
            results=results_str,
            query=query,
        )
        return prompt

    def get_relevant_places(self, results: List) -> List[Tuple[str, str]]:
        """
        Returns
        -------
        relevant_places: List[Tuple[str, str]]
            A list of tuples, where each tuple is (address, name)

        """
        # We use a dict to preserve ordering, while enforcing uniqueness
        relevant_places = dict()
        for result in results:
            if "formatted_address" in result and "name" in result:
                relevant_places[(result["formatted_address"], result["name"])] = None
            elif "formatted_address" in result and "for_location" in result:
                relevant_places[
                    (result["formatted_address"], result["for_location"])
                ] = None
            elif "vicinity" in result and "name" in result:
                relevant_places[(result["vicinity"], result["name"])] = None

        relevant_places = list(relevant_places.keys())

        if not relevant_places:
            current_location = self.tools.get_current_location()
            relevant_places.append((current_location, current_location))

        return relevant_places

    def get_place_dropdown_choices(
        self, relevant_places: List[Tuple[str, str]]
    ) -> List[str]:
        return [p[1] for p in relevant_places]

    def get_gmaps_html(self, relevant_place: Tuple[str, str]) -> str:
        address, name = relevant_place
        return GMAPS_EMBED_HTML_TEMPLATE.format(
            address=quote(address), location=quote(name)
        )

    def get_gmaps_html_from_dropdown(
        self, place_name: str, relevant_places: List[Tuple[str, str]]
    ) -> str:
        relevant_place = [p for p in relevant_places if p[1] == place_name][0]
        return self.get_gmaps_html(relevant_place)

    def _set_client_ip(self, request: gr.Request) -> None:
        client_ip = request.client.host
        if (
            "headers" in request.kwargs
            and "x-forwarded-for" in request.kwargs["headers"]
        ):
            x_forwarded_for = request.kwargs["headers"]["x-forwarded-for"]
        else:
            x_forwarded_for = request.headers.get("x-forwarded-for", None)
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()

        self.tools.client_ip = client_ip


demo = RavenDemo(DemoConfig.load_from_env())

if __name__ == "__main__":
    demo.launch(
        share=True,
        allowed_paths=["logo.png", "NexusRaven.png"],
        favicon_path="logo.png",
    )
