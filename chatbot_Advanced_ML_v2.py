import os
import re  # ✅ Required for regular expressions
from urllib.parse import quote  # ✅ Required for URL formatting
import streamlit as st
from SPARQLWrapper import SPARQLWrapper, JSON  # ✅ Remove duplicate imports

def format_entity_name(entity):
    """Formats the entity name to match DBpedia resource names."""
    if not entity:  # ✅ Prevents errors if entity is empty
        return None

    entity = entity.strip().rstrip("?").rstrip("_")
    entity = re.sub(r"^the\s+", "", entity, flags=re.IGNORECASE)
    entity = entity.title().replace(" ", "_")
    entity = quote(entity, safe="_") 
    return entity

def question_to_sparql(question):
    """Generates a SPARQL query based on the input question."""
    question_lower = question.lower().strip("?")

    # ✅ Check if the question is valid before processing
    if not question_lower or len(question_lower.split()) < 2:
        st.write("DEBUG: Invalid question format!")
        return None

    # ✅ Fix for "Who wrote The Catcher in the Rye?"
    if question_lower.startswith("who wrote "):
        entity = question[10:].strip()
        if not entity:
            st.write("DEBUG: No entity found in question!")
            return None

        special_cases = {"the catcher in the rye": "The_Catcher_in_the_Rye"}
        dbpedia_resource = special_cases.get(entity.lower(), format_entity_name(entity))

        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>
        SELECT ?authorName
        WHERE {{
          dbr:{dbpedia_resource} dbo:author ?author .
          ?author rdfs:label ?authorName .
          FILTER(lang(?authorName) = "en")
        }}
        LIMIT 1
        """
        return query

    # ✅ What is the capital of X?
    if question_lower.startswith("what is the capital of "):
        entity = question[22:].strip()
        if not entity:
            st.write("DEBUG: No entity found in question!")
            return None

        dbpedia_resource = format_entity_name(entity)
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>
        SELECT ?capitalName
        WHERE {{
          dbr:{dbpedia_resource} dbo:capital ?capital .
          ?capital rdfs:label ?capitalName .
          FILTER(lang(?capitalName) = "en")
        }}
        LIMIT 1
        """
        return query

    # ✅ What is the population of X?
    if question_lower.startswith("what is the population of "):
        entity = question[26:].strip()
        if not entity:
            st.write("DEBUG: No entity found in question!")
            return None

        dbpedia_resource = format_entity_name(entity)
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>
        SELECT ?population
        WHERE {{
          dbr:{dbpedia_resource} dbo:populationTotal ?population .
        }}
        LIMIT 1
        """
        return query

    # ✅ Where is X?
    if question_lower.startswith("where is "):
        entity = question[9:].strip()
        if not entity:
            st.write("DEBUG: No entity found in question!")
            return None

        dbpedia_resource = format_entity_name(entity)
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?locationName
        WHERE {{
          dbr:{dbpedia_resource} dbo:location ?location .
          ?location rdfs:label ?locationName .
          FILTER(lang(?locationName) = "en")
        }}
        LIMIT 1
        """
        return query

    # ✅ What is X famous for?
    if question_lower.startswith("what is ") and "famous for" in question_lower:
        entity = question[8:].replace("famous for", "").strip()
        dbpedia_resource = format_entity_name(entity)
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>
        SELECT ?abstract
        WHERE {{
          dbr:{dbpedia_resource} dbo:abstract ?abstract .
          FILTER(lang(?abstract) = "en")
        }}
        LIMIT 1
        """
        return query

    # ✅ When is X's birthdate?
    if question_lower.startswith("when is "):
        entity = question[8:].strip()  
        if not entity:
            st.write("DEBUG: No entity found in question!")
            return None

        dbpedia_resource = format_entity_name(entity)
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>
        SELECT ?birthDate
        WHERE {{
          dbr:{dbpedia_resource} dbo:birthDate ?birthDate .
        }}
        LIMIT 1
        """
        return query

    return None

def execute_sparql(query):
    """Executes the SPARQL query and returns the results."""
    if not query:
        st.write("DEBUG: No query generated!")
        return None

    sparql = SPARQLWrapper("https://dbpedia.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        results = sparql.query().convert()
        return results
    except Exception as e:
        st.write("SPARQL Execution Error:", e)
        return None

def result_to_text(results):
    """Formats the SPARQL results into readable text output."""
    if not results:
        return "No results found."

    bindings = results.get("results", {}).get("bindings", [])
    if not bindings:
        return "No results found."

    output = "Answer:\n"
    first_result = bindings[0]  # Take only the first result
    for key, value in first_result.items():
        output += f"- {value['value']}\n"
    return output

# 🚀 Streamlit Web App UI
st.title("DBpedia Chatbot")
st.write("Ask me a question, and I'll fetch the answer from DBpedia!")

# 🌟 User enters a question
user_question = st.text_input("Enter your question:")

if user_question:
    sparql_query = question_to_sparql(user_question)  
    if sparql_query:
        results = execute_sparql(sparql_query)  
        output = result_to_text(results)  # Formatting the output 
        st.write(output)  # Displaying only the answer
    else:
        st.write("I don't know how to answer that question yet.")
