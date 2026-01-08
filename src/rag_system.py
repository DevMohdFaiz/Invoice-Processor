import os
import sqlite3
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from .db_setup import ReceiptDB
receipt_db = ReceiptDB()

# llm = 
     
def vector_search_db(query, num_matches=5):
        """Retrieve semantically matching docs from the vectordb"""
        retriever = receipt_db.vectorstore.as_retriever(search_kwargs={"k": num_matches*10}) #I mulitplied k by 10 so as to get a very large base from which we can make unique extractions
        response = retriever.invoke(query)
        seen_ids = set()
        unique_res = []

        for doc in response: #helps get unique responses
            receipt_id= doc.metadata['receipt_id']
            if receipt_id not in seen_ids:
                seen_ids.add(receipt_id)
                unique_res.append(doc)
            if len(unique_res)>=num_matches:
                break

        unique_ids = [r.metadata['receipt_id'] for r in unique_res]

        with sqlite3.connect(receipt_db.sql_db) as conn:
            cursor = conn.cursor()
            matched_receipts, matched_items =[], []
            for receipt_id in unique_ids:
                cursor.execute("SELECT * FROM receipts where id = ?", (receipt_id,))
                receipt = cursor.fetchone()
                matched_receipts.append(receipt)
                cursor.execute("SELECT * FROM line_items where receipt_id = ?", (receipt_id,))
                item = cursor.fetchone()
                matched_items.append(item)
        conn.close()
        return [matched_receipts, matched_items]

class LLMChains():
    """LLM Chains based on user query"""
    def __init__(self):
        self.llm = ChatGroq(api_key=os.environ["GROQ_API_KEY"], model="openai/gpt-oss-120b", temperature=.4)
        self.sql_db = SQLDatabase.from_uri("sqlite:///db/receipts_sql_db/receipts.db")
        self.sql_toolkit = SQLDatabaseToolkit(db=self.sql_db, llm=self.llm)

    def vector_chain(self, query, num_matches:int =5):
        matched_receipts, matched_items = vector_search_db(query)

        system_prompt = ChatPromptTemplate.from_template("""
        You are an expert AI assistant at answering user questions about their receipts.
        The receipts have been embedded and stored in a vector database.
        You have access to two lists which are fetched from the vector database based on the user question.

        The first list contains {num_matches} receipts which have been retrieved from the vector database based on the user input.
        The first list values which represent the following respectively:
        [id , receipt_number TEXT, date TEXT, vendor_name, tax, subtotal, total, payment_method, created_at, creation_timestamp, additional_information]
        
        The first list is given below as:
        <context>{matched_receipts}</context>

        The **second list** contains {num_matches} line items which have been retrieved from the vector database based on the user input.
        The second list contains values which represent the following respectively:
        [id, receipt_id, description, quantity,  unit_price, total_price]

        The second list is given below as:
        <context>{matched_items}</context>

        The user question is given below:
        {query}

        Return an appropriate and suitable response to the user query using information from the **matched_receipts** and **matched items** lists
        """)
        chain = system_prompt | self.llm
        return chain.invoke({"matched_receipts": matched_receipts, "matched_items": matched_items, "query": query, "num_matches": num_matches})


    def sql_chain(self, query:str, top_k:int =5):
        """Chain to write SQL queries to answer user questions"""
        sql_tools = self.sql_toolkit.get_tools()
        print(f"sql dialect: {self.sql_db.dialect}")
        print(f"Available tables: {self.sql_db.get_usable_table_names()}")
        for tool in sql_tools:
            print(f"{tool.name}: {tool.description}\n")

        system_prompt = (f"""
        You are an agent designed to interact with a SQL database.
        Given an input question, create a syntactically correct {self.sql_db.dialect} query to run,
        then look at the results of the query and return the answer. Unless the user
        specifies a specific number of examples they wish to obtain, always limit your
        query to at most {top_k} results.

        You can order the results by a relevant column to return the most interesting
        examples in the database. Never query for all the columns from a specific table,
        only ask for the relevant columns given the question.

        You MUST double check your query before executing it. If you get an error while
        executing a query, rewrite the query and try again.

        DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
        database.

        To start you should ALWAYS look at the tables in the database to see what you
        can query. Do NOT skip this step.

        Then you should query the schema of the most relevant tables.
                                                         
        The user question is given below as:
        <context>{query}</context>
        """)

        agent = create_agent(model=self.llm, tools=sql_tools, system_prompt=system_prompt)
        # chain = system_prompt | agent
        # return chain.invoke({"sql_db_dialect": self.sql_db_dialect, "top_k": top_k, "query": query})
        return agent.invoke({"messages": [{"role": "user", "content": query}]})
    
        # response = agent.invoke({"messages": [{
        #     "role": "user", "content": query
        # }]})
        return response
    
    
