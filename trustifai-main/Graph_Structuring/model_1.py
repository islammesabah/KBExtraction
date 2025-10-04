from spacy import load
import json

allowed_dependencies = {
     'acomp','advmod','agent','amod','attr','aux','auxpass',
     'case','cc','ccomp','compound','conj','det','dobj',
     'nmod','nsubj','nsubjpass',
     'pcomp','pobj','prep','poss','ROOT','xcomp'
}

def has_required_dependencies(doc, allowed_dependencies):
    if not {token.dep_ for token in doc}.issubset(allowed_dependencies):
        return False

    return ("is a" in doc.text.lower() or "is an" in doc.text.lower()) or \
            (any(token.dep_ == 'ROOT' for token in doc) and \
            any(token.dep_ in {'nsubj', 'nsubjpass'} for token in doc) and \
            any(token.dep_ in {'dobj', 'pobj'} for token in doc))

nlp = load("en_core_web_sm")
unhandled_sentences=set()
all_graphs = []

def handle_sentence(sentence):
    doc = nlp(sentence)
    
    # displacy.render(doc, style="dep", jupyter=True, options={'distance': 90})
    if not has_required_dependencies(doc, allowed_dependencies):
        return False, sentence

    try:
        temp_graph = {
            "nodes": {},  # {'nodes': {0: {'pos': 0, 'label': 'X', 'dep': 'nsubj'}, 4: {'pos': 4, 'label': 'Y', 'dep': 'pobj'}},
            "edges": [],  # 'edges': [(0, 4, 'is subclass of')]}
            "sentence": sentence
        }

        edge_mapping = {
            'subject_nodes': {},  # {1: {0}} # multiple subject nodes possible
            'object_nodes': {},   # {1: 4}
            'edge_ids': set()     # {1}
        }

        temp_graph["nodes"] = {token['id']: {"pos": token['id'], "label": doc.text, "dep": token['dep']}
                            for token, doc in zip(doc.to_json()['tokens'], doc)}

        temp_graph["edges"] = [(token['head'], token['id'], token['dep'])
                                for token in doc.to_json()['tokens'] if token['head'] != token['id']]

        root_node = list(filter(lambda node: temp_graph["nodes"][node]['dep'] == 'ROOT', temp_graph["nodes"]))[0]
        stopping = False
        while not stopping:
            for edge in sorted(temp_graph["edges"], key=lambda x: abs(x[0] - x[1])):

                source_pos, target_pos, meta = edge

                if source_pos not in temp_graph["nodes"] or target_pos not in temp_graph["nodes"]:
                    continue
                print(edge)
                source_metadata = temp_graph["nodes"][source_pos]
                target_metadata = temp_graph["nodes"][target_pos]
                try:
                    match (source_metadata, meta, target_metadata):

                        case {'label': s, **source}, 'compound' | 'amod' | 'aux' |'auxpass' | 'advmod', {'label': t, **target}:
                            source_metadata['label'] = f"{t} {s}"
                            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges']))
                            del temp_graph['nodes'][target_pos]
                            continue

                        case {'label': s, **source}, 'agent', {'label': t, **target}:
                            source_metadata['label'] = f"{s} {t}"
                            next_node = next((n for src, n, label in temp_graph["edges"] if src == target_pos and label == 'pobj'), None)
                            edge_mapping['edge_ids'].add(source_pos)
                            edge_mapping['object_nodes'][source_pos] = next_node
                            temp_graph['edges'].append((source_pos, next_node, 'pobj'))
                            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges']))
                            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == target_pos and edge[1] == next_node), temp_graph['edges']))
                            del temp_graph['nodes'][target_pos]
                            continue

                        case {'label': s, **source}, 'case' | 'cc', {'label': t, **target}:
                            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges']))
                            del temp_graph['nodes'][target_pos]
                            continue

                        case {'label': s, **source}, 'det', {'label': t, **target}:
                            temp_graph['nodes'][source_pos]['det'] = t
                            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges']))
                            del temp_graph['nodes'][target_pos]
                            continue

                        case {'label': s, **source}, 'attr'|'acomp', {'label': 'subclass'|'attribute'|'dimension'|'kind'|'threat'|'result'|'type'|'equal'|'form', **target}: #is(head)--attr--subclass(tail)--prep--of(child)--pobj--Risk
                            next_node = next((n for src, n, label in temp_graph["edges"] if src == target_pos and label == 'prep'), None)
                            obj_node = next((n for src, n, label in temp_graph["edges"] if src == next_node and label == 'pobj'), None)
                            source_metadata['label'] = f"{s} {target_metadata['label']} {temp_graph['nodes'][next_node]['label']}" #is-->issubclassof
                            edge_mapping['edge_ids'].add(source_pos)
                            edge_mapping['object_nodes'][source_pos] = obj_node
                            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges'])) # remove edge: is--subclass
                            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == target_pos and edge[1] == next_node), temp_graph['edges'])) # remove edge: subclass--of
                            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == next_node and edge[1] == obj_node), temp_graph['edges'])) # remove edge: of--Y
                            temp_graph['edges'].append((source_pos, obj_node, 'pobj')) #connect edge from 'is' node to obj node
                            del temp_graph['nodes'][target_pos] # remove node: 'subclass'
                            del temp_graph['nodes'][next_node]  # remove node: 'of'
                            continue

                        case {'label': s, **source}, 'attr'|'acomp', {'label': t, **target}: #is-attr-Y
                            edge_mapping['edge_ids'].add(source_pos)
                            edge_mapping['object_nodes'][source_pos] = target_pos
                            continue

                        case {'dep': 'ROOT', 'label': s, **source}, 'prep'|'xcomp', {'label': t, **target}: #attributes(ROOT)--prep--to #helps--xcomp--see--pobj--X
                            source_metadata['label'] = f"{s} {t}"
                            next_node = next((n for src, n, label in temp_graph["edges"] if src == target_pos and label in {'pobj', 'dobj'}), None)
                            if next_node:
                                temp_graph['edges'].append((source_pos, next_node, 'pobj'))
                                temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges']))
                                temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == target_pos and edge[1] == next_node), temp_graph['edges']))
                            del temp_graph['nodes'][target_pos]
                            continue

                        case {'label': s, **source}, 'prep', {'label': t, **target}: #*-dobj-assessment--prep--of|*-attr-(a)dimension-prep-of
                            if next((n for src, n, label in temp_graph["edges"] if n == source_pos and label == 'attr'), None) is None:
                                next_node = next((n for src, n, label in temp_graph["edges"] if src == target_pos and label in {'pobj'}), None)
                                if next_node: #Date-prep-of-pobj-birth
                                    source_metadata['label'] = f"{s} {t} {temp_graph['nodes'][next_node]['label']}"
                                    temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges']))
                                    temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == target_pos and edge[1] == next_node), temp_graph['edges']))
                                    del temp_graph['nodes'][target_pos]
                                    del temp_graph['nodes'][next_node]
                                else:
                                    edge_mapping['edge_ids'].add(target_pos)
                                    edge_mapping['subject_nodes'].setdefault(target_pos, set()).add(source_pos)
                                    temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges']))
                            continue

                        case {'label': s, **source}, 'poss', {'label': t, **target}:
                            next_node = next((n for src, n, label in temp_graph["edges"] if src == source_pos and label == 'conj'), None)
                            if next_node:
                                temp_graph['edges'].append((temp_graph["nodes"][next_node]['label'],
                                                        temp_graph["nodes"][target_pos]['label'],
                                                        'of'))
                            continue

                        case {'label': s, **source}, 'nmod', {'label': t, **target}:
                            source_metadata['label'] = f"{t} {s}"
                            incoming_node = next((src for src, n, label in temp_graph["edges"] if target == source_pos and label == 'nsubj'), None)
                            if 'conj' in target:
                                target['conj']['nodeId'] = target['conj']['text'] + f" {s}"
                                edge_mapping['subject_nodes'][incoming_node].add(target['conj']['nodeId'])
                            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges']))
                            del temp_graph['nodes'][target_pos]
                            continue

                        case {'label': s, **source}, 'conj', {'label': t, **target}:
                            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges']))
                            temp_graph['nodes'][source_pos]['conj'] = {'text': t, 'nodeId': target_pos}
                            continue

                        case {'label': s, **source}, 'pcomp', {'label': t, **target}: #in--pcomp--explaining--dobj--x
                            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges']))
                            next_node = next((n for src, n, label in temp_graph["edges"] if src == target_pos and label in {'pobj', 'dobj'}), None)
                            if next_node:
                                temp_graph['nodes'][root_node]['label'] += f" {t}"  #if not work f" {temp_graph['nodes'][root_node]['label']} {t}
                                temp_graph['edges'].append((root_node, next_node, 'dobj'))
                                temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == target_pos and edge[1] == next_node), temp_graph['edges']))
                                del temp_graph['nodes'][source_pos]
                                del temp_graph['nodes'][target_pos]
                            continue

                        case {'label': s, **source}, 'ccomp', {'label': t, **target}: #Design interface can help users understand AI decisions
                            next_node = next((n for src, n, label in temp_graph["edges"] if src == target_pos and label == 'nsubj'), None)
                            if next_node:
                                edge_mapping['object_nodes'][source_pos] = next_node
                            continue

                        case {'label': s, **source}, 'nsubj' | 'nsubjpass', {'label': t, **target}:
                            edge_mapping['edge_ids'].add(source_pos)
                            edge_mapping['subject_nodes'].setdefault(source_pos, set()).add(target_pos)
                            if 'conj' in target:
                                edge_mapping['subject_nodes'][source_pos].add(target_metadata['nodeId'])
                            continue

                        case {'label': s, **source}, 'dobj' | 'pobj', {'label': t, **target}:
                            if next((src for src, n, label in temp_graph["edges"] if src == source_pos and label == 'prep'), None):
                                source_metadata['label'] = f"{s} {t}"
                                temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == source_pos and edge[1] == target_pos), temp_graph['edges']))
                                del temp_graph['nodes'][target_pos]
                            #assign object outside loop
                            continue

                        case another:
                            print("another:", edge)
                            unhandled_sentences.add(sentence)
                            stopping = True
                            continue

                except Exception as e:
                        print(f"Error occurred in sentence: {sentence} with edge: {edge}, error: {e}")
                        unhandled_sentences.add(sentence) # throw error
                        stopping = True
                        continue

        # Update object nodes
        edge_mapping['object_nodes'].update({
            edge_id: next((tail for head, tail, meta in temp_graph['edges']
                        if meta in {'dobj', 'pobj'}), None)
            for edge_id in edge_mapping['edge_ids']
            if edge_id not in edge_mapping['object_nodes']
        })

        for edge_id, obj_node in edge_mapping['object_nodes'].items():
            if obj_node is None:
                print(f"Missing object node for edge ID: {edge_id}")

        # create final mapping
        for edge_id in edge_mapping['edge_ids']:
            subject_nodes = edge_mapping['subject_nodes'][edge_id]
            object_node = edge_mapping['object_nodes'][edge_id]
            edge_node = temp_graph['nodes'][edge_id]
            for subject_node in subject_nodes:
                #temp_graph['edges'].append((subject_node, object_node, edge_node['label']))
                temp_graph['edges'].append((temp_graph["nodes"][subject_node]['label'],
                                            temp_graph["nodes"][object_node]['label'],
                                            edge_node['label']))
                temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == edge_id and edge[1] == subject_node), temp_graph['edges']))

            temp_graph['edges'] = list(filter(lambda edge: not (edge[0] == edge_id and edge[1] == object_node), temp_graph['edges']))
            del temp_graph['nodes'][edge_id]

        temp_graph['edges'] = list(set(temp_graph['edges'])-set([edge for edge in temp_graph['edges'] if edge[2] in allowed_dependencies]))

        #all_graphs.append(temp_graph)
        return True, {
        "edges": temp_graph["edges"],
        "sentence": temp_graph["sentence"]
        }
      

    except Exception as e:
        print(f"Failed to process sentence: {sentence}, error: {e}")
        return False, sentence



def model_1_extraction(data_path):
    with open(data_path, "r") as file:
        data = file.read()
    sentences = [s.strip().rstrip(string.punctuation) for s in sentences.strip().split('\n') if s.strip()]

    for sentence in sentences:
        status, result = handle_sentence(sentence)
        if status:
            all_graphs.append(result)
        else:
            unhandled_sentences.add(result)
    

model_1_extraction("Data/DSA/DSA_knowledge.txt")


with open("unhandled_sentences.txt", "w") as file:
  for unhandled in unhandled_sentences:
    file.write(unhandled + "\n")

# Training data - for fine tuning the HF model:
# Structure of json file is to be updated(current json edge has position of connected node, which we will change to node name)
with open('graph_data.json', 'w') as json_file:
    json.dump(all_graphs, json_file, indent=4, ensure_ascii=False)
