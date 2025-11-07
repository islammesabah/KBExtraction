import pandas as pd
import datetime
import uuid

class Logs:
    def __init__(self):
        try:
            self.data_table = self.load()
        except FileNotFoundError:
            self.reset_dataset()
            self.data_table= self.load()
        
    # load dataset from disk
    def load(self):
        data_table = pd.read_csv("Log/full_data.csv")
        return data_table
    
    # reset or generate the dataset
    def reset_dataset(self):
        data_table = pd.DataFrame(
            columns=[
                # manageral information
                "ID",
                "Timestamp",
                "Username",
                # Ground truth information
                "Exact_Text",
                "Filename",
                "Page_number",
                "Based_on",
                # System generated information
                "Decomposition",
                "Decom_user_decision",  # correct, not correct, update
                "Source",
                "s_user_decision"       # correct, not correct, update
                "Target",
                "t_user_decision",      # correct, not correct, update
                "Edge",
                "e_user_decision",     # correct, not correct, update
                # User updated information
                "Updated_decomposition",
                "Updated_source",
                "Updated_target",
                "Updated_edge",
            ]
        )
        data_table.to_csv("Log/full_data.csv", encoding='utf-8', index=False, header=True)
    
    # create a text information record
    def create_record_data(self, exact_text, filename, page_number, based_on):
        record = {
            "Exact_Text": exact_text,
            "Filename": filename,
            "Page_number": page_number,
            "Based_on": based_on
        }
        id = self.data_table.query(f'Exact_Text == "{record["Exact_Text"]}" and Username == "{record["Username"]}"')["ID"]
        if len(id) == 0:
            id = uuid.uuid4()
        else: 
            return 0
        timestamp =  datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_row = pd.Series({'ID':id,'Timestamp':timestamp, **record})

        self.data_table = pd.concat([
                self.data_table, 
                pd.DataFrame([new_row], columns=new_row.index)]
           ).reset_index(drop=True)
        self.data_table.to_csv("Log/data.csv", encoding='utf-8', index=False, header=True)
        return id

    def add_log(self, id, username, type, decomposition, user_decision, Updated_decomposition=None):
        # Check if the ID for the exact user exists in the data_table
        if not self.data_table.query(f'ID == "{id}" and Username == "{username}"').empty:
            # Update the Decomposition column for the given ID and Username
            self.data_table.loc[(self.data_table['ID'] == id) & (self.data_table['Username'] == username), 'Decomposition'] = decomposition
            # Update the user_decision column for the given ID and Username
            self.data_table.loc[(self.data_table['ID'] == id) & (self.data_table['Username'] == username), 'Decom_user_decision'] = user_decision
            # Update the Updated_decomposition column for the given ID and Username if it is provided
            if Updated_decomposition:
                self.data_table.loc[(self.data_table['ID'] == id) & (self.data_table['Username'] == username), 'Updated_decomposition'] = Updated_decomposition
            
            # Save the updated data_table to CSV
            self.data_table.to_csv("Log/full_data.csv", encoding='utf-8', index=False, header=True)

    def add_llm_source(self, id, username, source, user_decision, Updated_source=None):
        # Check if the ID for the exact user exists in the data_table
        if not self.data_table.query(f'ID == "{id}" and Username == "{username}"').empty:
            # Update the Source column for the given ID and Username
            self.data_table.loc[(self.data_table['ID'] == id) & (self.data_table['Username'] == username), 'Source'] = source
            # Update the user_decision column for the given ID and Username
            self.data_table.loc[(self.data_table['ID'] == id) & (self.data_table['Username'] == username), 's_user_decision'] = user_decision
            # Update the Updated_source column for the given ID and Username if it is provided
            if Updated_source:
                self.data_table.loc[(self.data_table['ID'] == id) & (self.data_table['Username'] == username), 'Updated_source'] = Updated_source
            
            # Save the updated data_table to CSV
            self.data_table.to_csv("Log/full_data.csv", encoding='utf-8', index=False, header=True)

    def add_llm_decomposition(self, id, username, decomposition, user_decision, Updated_decomposition = None):
        # Check if the ID for exact user exists in the data_table
        if id in self.data_table['ID'].values:
            # Update the Decomposition column for the given ID
            self.data_table.loc[self.data_table['ID'] == id, 'Decomposition'] = decomposition
            # Update the timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.data_table.loc[self.data_table['ID'] == id, 'Timestamp'] = timestamp
            # Save the updated data_table to CSV
            self.data_table.to_csv("Log/full_data.csv", encoding='utf-8', index=False, header=True)
        else:
            print(f"ID {id} not found in the data_table")

    # add logging updates of the user
    def add_llm_decomposition(self,id,decomposition):
         # Input relation:
        # {
        #     'source': {
        #         'label': edge[0]
        #     },
        #     'target': {
        #         'label': edge[1]
        #     },
        #     'edge': {
        #         'label': edge[2],
        #         'properties': {
        #             'sentence': edge_object["sentence"],
        #             "original_sntence": sentence_doc.page_content, 
        #             **sentence_doc.metadata
        #         }

        #     },
        # }
        record = {
            "Decomposition": decomposition,
    
        }
        id = self.data_table.query(f'Decomposition == "{record["Decomposition"]}"')["ID"]
        if len(id) > 0:
            id = id.iloc[0]
        else: 
            return
        timestamp =  datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_row = pd.Series({'ID':id,'Timestamp':timestamp, **record})

        self.user_update_table = pd.concat([
                self.user_update_table, 
                pd.DataFrame([new_row], columns=new_row.index)]
           ).reset_index(drop=True)
        self.user_update_table.to_csv("Log/user_updates.csv", encoding='utf-8', index=False, header=True)


#test
# if __name__ == "__main__":
#     d = Logs()
    # d.reset_dataset()
    # d.add_record_data({
    #     "Decomposition":"ff"
    # })
    # d.add_user_update({
    #     "Decomposition":"ff"
    # })
    # d.add_user_update({
    #     "Decomposition":"h"
    # })