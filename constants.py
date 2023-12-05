RAVEN_GENERATION_KWARGS = {
    "max_new_tokens": 200,
    "do_sample": False,
    "temperature": 0.001,
    "return_full_text": False,
    "stop_sequences": ["<bot_end>"],
    "stream": True,
}

SUMMARY_MODEL_PROMPT = """GPT4 Correct User: Please answer the following query using natural language based on the search results below with no extra hallucinated content. When there is no relevant information in the search results, please do not answer extra information and answer with "No relevant information". Please keep your response concise. 
For your reference, the current location is {current_location} and the current time is {current_time}.

Query: {query}

Search results:
{results}
<|end_of_turn|>GPT4 Correct Assistant: """

SUMMARY_MODEL_GENERATION_KWARGS = {
    "max_new_tokens": 1000,
    "do_sample": False,
    "temperature": 0.001,
    "return_full_text": False,
    "stream": True,
}

EXAMPLE_QUERIES = {
    "Discover Your Locale": "Get me good food nearby?",
    "Gather Opinions": "What are people saying about Golden Gate Park in San Francisco?",
    "Compare Feedback": "Can you get me reviews for So Gong Dong Tofu house and Siam Thai Cuisine in San Jose and compare them specifically regarding how tasty the food is? Summarize the answer. Please print the review texts you reference.",
    "Tailored Recommendations": "Get me some good vegetarian Chinese food in San Francisco?",
    "Proximity Searches": "Can you list me hostels that are cheaper than $200 per night? I need the place to be within 20 miles from San Francisco City Hall.",
    "Deep Insights": "Can you please compare the reviews for Ippudo Ramen, Ramen Nagi and Yayoi Cupertino?",
}

INTRO_TEXT = """
# Google Places API Copilot Demo, Driven by NexusRaven-V2 13B
This demo presents a natural language interface to the Google Places API, showcasing Raven's capability to enable copilots and agents to use software tools. Raven transforms your plain English queries into function calls to your APIs. Type in your query and lets explore wonderful places and recommendations through Raven and the Places API!

🗺️ Google Places API searches for places of interest and returns information regarding location, reviews, and recommendations.

🐦‍⬛ NexusRaven-V2 13B, our function calling model, will execute the necessary API calls in the backend to get the information you need!

### Examples
"""

CSS = """
footer {
    visibility: hidden;
}
.inner-large-font {
    --text-md: 16px;
    font-size: 20;
}
:root {
    --text-sm: 18px;
    --input-text-size: 18px;
}
.dark {
    --text-sm: 18px;
    --input-text-size: 18px;
}

"""

HEADER_HTML = """<img width="50" height="50" style="float:left; margin: 0px;" src="/file=logo.png">
<h1 style="overflow: hidden; padding-top: 17px; margin: 0px;">Nexusflow</h1>
"""

# Inputs must be encoded via urllib.parse.quote
GMAPS_EMBED_HTML_TEMPLATE = """
<iframe width="100%" height="600" frameborder="0" scrolling="no" marginheight="0" marginwidth="0" src="https://maps.google.com/maps?width=100%25&amp;height=600&amp;hl=en&amp;q={location}+{address}&amp;t=&amp;z=18&amp;ie=UTF8&amp;iwloc=B&amp;output=embed">
"""

ERROR_MESSAGE = "Sorry, I couldn't fulfill your request! Please try again :)"
