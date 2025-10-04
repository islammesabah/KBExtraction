from openai import OpenAI

#set the base url to the local server
client = OpenAI(base_url="http://serv-3306.kl.dfki.de:8000/v1", api_key="") 
#setting an api key is required from the openai framework, but the server itself does not use it
 
# get a list of models hosted on the local server
print(client.models.list())

# Call the ChatCompletion API

completion = client.chat.completions.create(  
    model="meta-llama-3.1-70b-instruct-fp8",  
    messages=[    
        {
            "role": "system", 
            "content": "You are a helpful assistant."
        },    
        {
            "role": "user", 
            "content": "Hello, are you there?"
        } 
     ])

#print the response
# print(completion.choices[0].message.content)