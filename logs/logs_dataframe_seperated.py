import pandas as pd
import datetime
import uuid

class Logs:
    def __init__(self):
        try:
            self.data_table, self.user_update_table = self.load()
        except FileNotFoundError:
            self.reset_dataset()
            self.data_table, self.user_update_table = self.load()
        
    # load dataset from disk
    def load(self):
        data_table = pd.read_csv("Log/data.csv")
        user_update_table = pd.read_csv("Log/user_updates.csv")
        return data_table, user_update_table
    
    # reset or generate the dataset
    def reset_dataset(self):
        data_table = pd.DataFrame(
            columns=[
                "ID",
                "Timestamp",
                "Text",
                "Decomposition",
                "Source",
                "Target",
                "Edge",
                "Page_number"
            ]
        )
        data_table.to_csv("Log/data.csv", encoding='utf-8', index=False, header=True)
        user_update_table = pd.DataFrame(
            columns=[
                "ID",
                "Timestamp",
                "Decomposition",
                "Updated_source",
                "Updated_target",
                "Updated_edge",
            ]
        )
        user_update_table.to_csv("Log/user_updates.csv", encoding='utf-8', index=False, header=True)
    
    # add logging for system generation 
    def add_record_data(self,relation):
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
            "Text" : relation["edge"]["properties"]["original_sntence"],
            "Decomposition": relation["edge"]["properties"]["sentence"],
            "Source":  relation["source"]["label"],
            "Target": relation["target"]["label"],
            "Edge": relation["edge"]["label"],
            "Page_number": relation["edge"]["properties"]["page_number"]
        }
        id = self.data_table.query(f'Decomposition == "{record["Decomposition"]}"')["ID"]
        if len(id) == 0:
            id = uuid.uuid4()
        else: 
            return
        timestamp =  datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_row = pd.Series({'ID':id,'Timestamp':timestamp, **record})

        self.data_table = pd.concat([
                self.data_table, 
                pd.DataFrame([new_row], columns=new_row.index)]
           ).reset_index(drop=True)
        self.data_table.to_csv("Log/data.csv", encoding='utf-8', index=False, header=True)

    # add logging updates of the user
    def add_user_update(self,relation):
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
            "Decomposition": relation["edge"]["properties"]["sentence"],
            "Updated_source":  relation["source"]["label"],
            "Updated_target": relation["target"]["label"],
            "Updated_edge": relation["edge"]["label"],
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