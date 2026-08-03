import json
from urllib.request import Request, urlopen
from urllib.error import URLError
from bs4 import BeautifulSoup
import time

def request(action, **params):
    return {'action': action, 'params': params, 'version': 6}

def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode('utf-8')
    response = json.load(urlopen(Request('http://127.0.0.1:8765', requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']

def getwikidef(word, lg="nl"):
    requesturl = f"https://en.wiktionary.org/api/rest_v1/page/definition/{word}?redirect=true"
    header = {'accept': 'application/json; charset=utf-8; profile="https://www.mediawiki.org/wiki/Specs/definition/0.8.0"', 'User-Agent': 'natsburnbin@gmail.com'}
    req = Request(requesturl, headers=header)
    try:
        with urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if lg in data:
                return data[lg]
            else:
                print(f"{word} was not found for language {lg}")
                return {}
    except URLError as e:
        if hasattr(e, 'reason'):
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
            return None
        elif hasattr(e, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
            return None

def getwikihtml(word):
    requesturl = f"https://en.wiktionary.org/api/rest_v1/page/html/{word}?redirect=true&stash=false"
    header = {'accept': 'text/html; charset=utf-8; profile="https://www.mediawiki.org/wiki/Specs/HTML/2.1.0"', 'User-Agent': 'natsburnbin@gmail.com'}
    req = Request(requesturl, headers=header)
    try:
        with urlopen(req) as response:
            data = response.read().decode('utf-8')
            return data
    except URLError as e:
        if hasattr(e, 'reason'):
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
            return None
        elif hasattr(e, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
            return None

def getconjugationhtml(word):
    req = f"https://www.mijnwoordenboek.nl/ww.php?woord={word}"
    try:
        with urlopen(req) as response:
            data = response.read().decode('utf-8')
            return data
    except URLError as e:
        if hasattr(e, 'reason'):
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
            return None
        elif hasattr(e, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
            return None

def organizedata(data):
    examples_with_translations = []
    cleaned_data = []
    for data_item in data:
        dictionary_entry = {}
        for key in data_item:
            value = data_item[key]
            if key == "definitions":
                value = []
                for defdictionary in data_item[key]: # this is checking the list of dictionaries (the defintions)
                    definition_entry = {"definition":"", "examples":[]}
                    for dictionkey in defdictionary: # this is checking every key in a dictionary (def, examples, parsedExamples)
                        if dictionkey == "parsedExamples":
                            examples_with_translations.extend(defdictionary[dictionkey])
                        elif dictionkey == "definition":
                            definition_entry[dictionkey] = BeautifulSoup(defdictionary[dictionkey], features="html.parser").get_text().strip()
                        elif dictionkey == "examples":
                            definition_entry[dictionkey] = []
                            for j in range(len(defdictionary[dictionkey])):
                                definition_entry[dictionkey].append(BeautifulSoup(defdictionary[dictionkey][j], features="html.parser").get_text().strip())
                        else:
                            print("OTHER VALUE DETECTED")
                            print(dictionkey)
                            print(defdictionary[dictionkey])
                            print("")
                    value.append(definition_entry)
            dictionary_entry[key] = value
        cleaned_data.append(dictionary_entry)
    return cleaned_data, examples_with_translations

def getnounattributes(word):
    html = getwikihtml(word)
    soup = BeautifulSoup(html, features='html.parser')
    
    dutch_start = soup.find(id="Dutch")
    if not dutch_start: return []

    attributes = []
    
    for element in dutch_start.find_all_next():
        if element.name == "h2":
            break
        if element.name in ['h3', 'h4', 'h5'] and "Noun" in (element.get('id', '')):
            attribute = {"gender": "", "plural":"", "diminutive":""}
            headword_line = element.find_next('p')
            gender_tag = headword_line.select_one('.gender abbr')
            if gender_tag:
                attribute["gender"] = gender_tag.text.strip()
            plural_tag = headword_line.select_one('b.p-form-of')
            if plural_tag:
                attribute["plural"] = plural_tag.get_text().strip()
            elif "uncountable" in headword_line.get_text().lower():
                attribute["plural"] = "uncountable"
            dim_tag = headword_line.select_one('b.diminutive-form-of')
            if dim_tag:
                attribute["diminutive"] = dim_tag.get_text().strip()

            attributes.append(attribute)
    return attributes

def getconjugations(word):
    html = getconjugationhtml(word)
    soup = BeautifulSoup(html, features='html.parser')
    
    tablestart = soup.find(id="post-203").find("table")
    if not tablestart:
        return None
    verb_data = {"Voltooid deelwoord":[], "Onvoltooid tegenwoordige tijd (ott)":[], "Voltooid tegenwoordige tijd (vtt)":[], "Onvoltooid verleden tijd (ovt)":[], "Gebiedende wijs":[]}

    rows = tablestart.find_all("tr")
    conjugations_form = ""
    for row in rows:
        cells = row.find_all("td")
        for br in cells[0].find_all("br"):
            br.replace_with("||<<BREAK>>||")
        rn = cells[0].get_text().split("||<<BREAK>>||")
        clean_rn = [val.strip() for val in rn if val.strip()]
        if conjugations_form:
            verb_data[conjugations_form] = clean_rn
            conjugations_form = ""
            continue
        if len(clean_rn) > 0 and clean_rn[0] in verb_data:
            conjugations_form = clean_rn[0]

    return verb_data

def filterforroots(Nouns, Verbs, Others, Examples):
    
    filteredNounsDefs = []
    filteredVerbsDefs = []
    filteredOthersDefs = []
    filteredExamples = []
    
    Redirects = []

    for i in range(len(Nouns)):
        filteredNounsDefs = []
        for j in range(len(Nouns[i]["definitions"])):
            if not Nouns[i]["definitions"][j]["definition"]:
                continue
            elif "plural of " == Nouns[i]["definitions"][j]["definition"][0:10]:
                Redirects.append({"Word":Nouns[i]["definitions"][j]["definition"][10:], "Type":"Noun"})
            elif "diminutive of " == Nouns[i]["definitions"][j]["definition"][0:14]:
                Redirects.append({"Word":Nouns[i]["definitions"][j]["definition"][14:], "Type":"Noun"})
            else:
                filteredNounsDefs.append(Nouns[i]["definitions"][j])
        Nouns[i]["definitions"] = filteredNounsDefs
    
    for i in range(len(Verbs)):
        filteredVerbsDefs = []
        for j in range(len(Verbs[i]["definitions"])):
            if not Verbs[i]["definitions"][j]["definition"]:
                continue
            elif "inflection of " == Verbs[i]["definitions"][j]["definition"][0:14]:
                Redirects.append({"Word":Verbs[i]["definitions"][j]["definition"].split(":")[0][14:], "Type":"Verb"})
                filteredVerbsDefs = []
                break
            else:
                filteredVerbsDefs.append(Verbs[i]["definitions"][j])
        Verbs[i]["definitions"] = filteredVerbsDefs

    for i in range(len(Others)):
        filteredOthersDefs = []
        for j in range(len(Others[i]["definitions"])):
            if not Others[i]["definitions"][j]["definition"]:
                continue
            elif "past participle of " == Others[i]["definitions"][j]["definition"][0:19]:
                Redirects.append({"Word":Others[i]["definitions"][j]["definition"][19:], "Type":"Other"})
                break
            elif "present participle of " == Others[i]["definitions"][j]["definition"][0:22]:
                Redirects.append({"Word":Others[i]["definitions"][j]["definition"][22:], "Type":"Other"})
                break
            elif "inflection of " == Others[i]["definitions"][j]["definition"].split(":")[0][0:14]:
                Redirects.append({"Word":Others[i]["definitions"][j]["definition"].split(":")[0][14:], "Type":"Other"})
                filteredOthersDefs = []
                break
            else:
                filteredOthersDefs.append(Others[i]["definitions"][j])
        Others[i]["definitions"] = filteredOthersDefs

    for example in Examples:
        if "example"  in example.keys() and "translation" in example.keys():
            filteredExamples.append(example)
    Examples = filteredExamples

    Nouns = [noun for noun in Nouns if noun["definitions"]]
    Verbs = [verb for verb in Verbs if verb["definitions"]]
    Others = [other for other in Others if other["definitions"]]

    return Nouns, Verbs, Others, Examples, Redirects

def extractwikidata(wikidata, word):
    cleaned_wikidata, example_sentences = organizedata(wikidata)
    Nouns = []
    Verbs = []
    Others = []
    for entry in cleaned_wikidata:
        if entry["partOfSpeech"] == "Noun":
            Nouns.append(entry)
        elif entry["partOfSpeech"] == "Verb":
            Verbs.append(entry)
        else:
            Others.append(entry)
    Nouns, Verbs, Others, example_sentences, Redirects = filterforroots(Nouns, Verbs, Others, example_sentences)
    if Nouns:
        attributes = getnounattributes(word)
        for i in range(len(Nouns)):
            attribute = attributes.pop(0) if attributes else {"gender":"", "plural":"", "diminutive":""}
            Nouns[i]["gender"] = attribute["gender"]
            Nouns[i]["plural"] = attribute["plural"]
            Nouns[i]["diminutive"] = attribute["diminutive"]
    if Verbs:
        conjugations = getconjugations(word)
        for i in range(len(Verbs)):
            Verbs[i]["conjugations"] = conjugations
            Verbs[i]["double_check"] = len(Verbs) > 1
    return Nouns, Verbs, Others, Redirects, example_sentences

def wait_for_anki():
    print("Waiting for Anki-Connect to respond...\n")
    seconds = 0
    while seconds < 90:
        try:
            invoke('deckNames')
            return True
        except Exception:
            time.sleep(1)
            seconds = seconds + 1
    print("Failed to open Anki")
    return False

def check_setup():
    currentdecks = invoke("deckNames")
    if ("Nederlands" not in currentdecks):
        invoke("createDeck", deck="Nederlands")
        print("Nederlands deck created")

    modelNames = invoke("modelNames")

    if "Nederlandse woord" not in modelNames:
        params = {
        "modelName": "Nederlandse woord",
        "inOrderFields": ["wordId", "word", "num", "isNoun", "isVerb", "isOther", "gender", "plural", "diminutive", "conjugations", "doubleCheck", "link", "definitionAndExamples"],
        "css": """
            .card {
                font-family: 'Consolas';
                text-align: center;
                color: navy !important;
            }
            .card-front, .card-back {
                position: relative;
                margin: 20px auto;
                padding: 20px;
                width: 280px;
                min-height: 380px;
                background-color: bisque;
                display: flex;
                flex-direction: column;
                justify-content: center; 
                align-items: center;
            }

            .cornernum {
                position: absolute;
                top: 10px;   
                left: 10px; 
                font-size: 30px;
                font-family: 'Consolas';
                color: navy;
                font-weight: bold;
            }
            .word-stack {
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .article { font-size: 20px; margin-bottom: -5px; }
            .word { font-size: 45px; font-weight: bold; }
            .grammar-info { font-size: 18px; margin: 10px 0; font-style: italic; }
            .conj-info { font-size: 12px; margin: 10px 0; font-style: italic; }
            .meaning { font-size: 15px; margin-top: 15px; }
            #answer { width: 90%; border: 0; border-top: 1px solid rgba(0,0,128,0.15); margin: 15px 0; }
        """,
        "cardTemplates": [
            {
                "Name": "Noun Card",
                "Front": """{{#isNoun}}
                            <div class="card-front">
                                {{#num}}<div class="cornernum">[{{num}}]</div>{{/num}}
                                <div class="word">{{word}}</div>
                                <div style="font-size:15px">(Noun)</div>
                            </div>
                            {{/isNoun}}""",
                "Back": """<div class="card-back">
                                {{#num}}<div class="cornernum">[<a href="{{text:link}}">{{num}}</a>]</div>{{/num}}
                                <div class="word-stack">
                                    {{#gender}}<div class="article">{{gender}}</div>{{/gender}}
                                    <div class="word">{{word}}</div>
                                </div>
                                <hr id="answer">
                                <div class="grammar-info">
                                    {{#plural}}<span>{{plural}}</span>{{/plural}}
                                    {{#plural}}{{#diminutive}} · {{/diminutive}}{{/plural}}
                                    {{#diminutive}}<span>{{diminutive}}</span>{{/diminutive}}
                                </div>
                                <div class="meaning">{{definitionAndExamples}}</div>
                            </div>"""
            },
            {
                "Name": "Verb Card",
                "Front": """{{#isVerb}}
                            <div class="card-front">
                                {{#num}}<div class="cornernum">[{{num}}]</div>{{/num}}
                                <div class="word">{{word}}</div>
                                <div style="font-size:15px">(Verb)</div>
                            </div>
                            {{/isVerb}}""",
                "Back": """<div class="card-back">
                                {{#num}}<div class="cornernum">[<a href="{{text:link}}">{{num}}</a>]</div>{{/num}}
                                <div class="word">{{word}}</div>
                                <hr id="answer">
                                <div class="conj-info">
                                    {{#conjugations}}{{conjugations}}{{/conjugations}}
                                    {{#doubleCheck}}
                                        <span class="check-link">
                                            <a href="{{text:doubleCheck}}">[*]</a>
                                        </span>
                                    {{/doubleCheck}}
                                </div>
                                <div class="meaning">
                                    {{definitionAndExamples}}
                                </div>
                            </div>"""
            },
            {
                "Name": "Other Card",
                "Front": """{{#isOther}}
                            <div class="card-front">
                                {{#num}}<div class="cornernum">[{{num}}]</div>{{/num}}
                                <div class="word">{{word}}</div>
                                <div style="font-size:15px">(Other)</div>
                            </div>
                            {{/isOther}}""",
                "Back": """ <div class="card-back">
                                {{#num}}<div class="cornernum">[<a href="{{text:link}}">{{num}}</a>]</div>{{/num}}
                                <div class="word">{{word}}</div>
                                <hr id="answer">
                                <div class="meaning">
                                    {{definitionAndExamples}}
                                </div>
                            </div>"""
            }
        ]}
        invoke("createModel", **params)
        print("Model for words created")

    if "Nederlandse voorbeelden met vertalingen" not in modelNames:
        params = {
        "modelName": "Nederlandse voorbeelden met vertalingen",
        "inOrderFields": ["example", "translation", "link"],
        "css": """
            .card {
                font-family: 'Consolas';
                text-align: center;
                color: navy !important;
            }
            .card-front, .card-back {
                position: relative;
                margin: 20px auto;
                padding: 20px;
                width: 280px;
                min-height: 380px;
                background-color: bisque;
                display: flex;
                flex-direction: column;
                justify-content: center; 
                align-items: center;
            }
            .cornernum {
                position: absolute;
                top: 10px;   
                left: 10px; 
                font-size: 30px;
                font-family: 'Consolas';
                color: navy;
                font-weight: bold;
            }

            .word { font-size: 20px; font-weight: bold; }
            .meaning { font-size: 15px; margin-top: 15px; }
            #answer { width: 90%; border: 0; border-top: 1px solid rgba(0,0,128,0.15); margin: 15px 0; }
        """,
        "cardTemplates": [
            {
                "Name": "Example to Translation",
                "Front": """
                            <div class="card-front">
                                <div class="word">{{example}}</div>
                            </div>
                        """,
                "Back": """<div class="card-back">
                                <div class="cornernum">[<a href="{{text:link}}">*</a>]</div>
                                <div class="word">{{example}}</div>
                                <hr id="answer">
                                <div class="meaning">{{translation}}</div>
                            </div>"""
            },
        ]}
        invoke("createModel", **params)
        print("Model for examples and translations created")

def mainloop():
    word = input("Enter 123 to exit \nEnter word: ")

    while(word != "123"):
        print("\nprocessing...")
        wikidata = getwikidef(word.replace(" ", "_"))
        if wikidata:
            Nouns, Verbs, Others, Redirects, example_sentences = extractwikidata(wikidata, word.replace(" ", "_"))

            link = f"https://en.wiktionary.org/wiki/{word.replace(" ", "_")}#Dutch"
            for i in range(len(Nouns)):
                noun = Nouns[i]
                article_of_gender = noun["gender"]
                if noun["gender"] == "m" or noun["gender"] == "f" or noun["gender"] == "c":
                    article_of_gender = "de"
                elif noun["gender"] == "n":
                    article_of_gender = "het"

                html_output = ""
                for j, entry in enumerate(noun["definitions"]):
                    html_output += f"<div>"
                    html_output += f"<div><b>{j+1}.</b> {entry['definition']}</div>"
                    html_output += "</div>"
                params = {
                    "note": {
                        "deckName": "Nederlands",
                        "modelName": "Nederlandse woord",
                        "fields": {
                            "wordId": f"{word} (Noun) [{i}]",
                            "word": word,
                            "num": f"{i}",
                            "isNoun": "TRUE",
                            "isVerb": "",
                            "isOther": "",
                            "gender": article_of_gender,
                            "plural": noun["plural"],
                            "diminutive": noun["diminutive"],
                            "conjugations": "",
                            "doubleCheck": "",
                            "link": link,
                            "definitionAndExamples": html_output
                        },
                        "options": {
                            "allowDuplicate": False,
                            "duplicateScope": "deck",
                            "duplicateScopeOptions": {
                                "deckName": "Nederlands",
                                "checkChildren": False,
                                "checkAllModels": False
                            }
                        },
                        "tags": [
                            "DutchNoun"
                        ]
                    }
                }
                try:
                    flashcard = invoke("addNote", **params)
                    print("+1 Noun card")
                except Exception as e:
                    print(f"Noun flashcard gen failed: {e}")
            
            for i in range(len(Verbs)):
                verb = Verbs[i]

                html_output = ""
                for j, entry in enumerate(verb["definitions"]):
                    html_output += f"<div>"
                    html_output += f"<div><b>{j+1}.</b> {entry['definition']}</div>"
                    html_output += "</div>"
                
                conjugations = ""
                
                if verb["conjugations"]:
                    conjkeys = verb["conjugations"].keys()
                    if "Onvoltooid tegenwoordige tijd (ott)" in conjkeys and "Onvoltooid verleden tijd (ovt)" in conjkeys and "Voltooid tegenwoordige tijd (vtt)" in conjkeys:
                        if len(verb["conjugations"]["Onvoltooid tegenwoordige tijd (ott)"]) >= 3 and len(verb["conjugations"]["Onvoltooid verleden tijd (ovt)"]) >= 3 and len(verb["conjugations"]["Voltooid tegenwoordige tijd (vtt)"]) >= 1:
                            conjugations = f"""<div>
                                    <span>{verb["conjugations"]["Onvoltooid tegenwoordige tijd (ott)"][0]}</span>
                                    · 
                                    <span>{verb["conjugations"]["Onvoltooid tegenwoordige tijd (ott)"][1]}</span>
                                    · 
                                    <span>{verb["conjugations"]["Onvoltooid tegenwoordige tijd (ott)"][2]}</span>
                                    </div>
                                    <div>
                                    <span>{verb["conjugations"]["Onvoltooid verleden tijd (ovt)"][0]}</span>
                                    · 
                                    <span>{verb["conjugations"]["Onvoltooid verleden tijd (ovt)"][1]}</span>
                                    · 
                                    <span>{verb["conjugations"]["Onvoltooid verleden tijd (ovt)"][2]}</span>
                                    </div>
                                    <div>
                                    {verb["conjugations"]["Voltooid tegenwoordige tijd (vtt)"][0]}
                                    </div>
                            """
                if verb["double_check"]:
                    doublecheck = f"https://en.wiktionary.org/wiki/{word.replace(" ", "_")}#Dutch"
                else:
                    doublecheck = ""
                params = {
                    "note": {
                        "deckName": "Nederlands",
                        "modelName": "Nederlandse woord",
                        "fields": {
                            "wordId": f"{word} (Verb) [{i}]",
                            "word": word,
                            "num": f"{i}",
                            "isNoun": "",
                            "isVerb": "TRUE",
                            "isOther": "",
                            "gender": "",
                            "plural": "",
                            "diminutive": "",
                            "conjugations": conjugations,
                            "doubleCheck": doublecheck,
                            "link": link,
                            "definitionAndExamples": html_output
                        },
                        "options": {
                            "allowDuplicate": False,
                            "duplicateScope": "deck",
                            "duplicateScopeOptions": {
                                "deckName": "Nederlands",
                                "checkChildren": False,
                                "checkAllModels": False
                            }
                        },
                        "tags": [
                            "DutchVerb"
                        ]
                    }
                }
                try:
                    flashcard = invoke("addNote", **params)
                    print("+1 Verb card")
                except Exception as e:
                    print(f"Verb flashcard gen failed: {e}")

            for i in range(len(Others)):
                other = Others[i]

                html_output = ""
                for j, entry in enumerate(other["definitions"]):
                    html_output += f"<div>"
                    html_output += f"<div><b>{j+1}.</b> {entry['definition']}</div>"
                    html_output += "</div>"
                params = {
                    "note": {
                        "deckName": "Nederlands",
                        "modelName": "Nederlandse woord",
                        "fields": {
                            "wordId": f"{word} (Other) [{i}]",
                            "word": word,
                            "num": f"{i}",
                            "isNoun": "",
                            "isVerb": "",
                            "isOther": "TRUE",
                            "gender": "",
                            "plural": "",
                            "diminutive": "",
                            "conjugations": "",
                            "doubleCheck": "",
                            "link": link,
                            "definitionAndExamples": html_output
                        },
                        "options": {
                            "allowDuplicate": False,
                            "duplicateScope": "deck",
                            "duplicateScopeOptions": {
                                "deckName": "Nederlands",
                                "checkChildren": False,
                                "checkAllModels": False
                            }
                        },
                        "tags": [
                            "DutchOther"
                        ]
                    }
                }
                try:
                    flashcard = invoke("addNote", **params)
                    print("+1 Other card")
                except Exception as e:
                    print(f"Other flashcard gen failed: {e}")
            
            for examplepair in example_sentences:
                params = {
                    "note": {
                        "deckName": "Nederlands",
                        "modelName": "Nederlandse voorbeelden met vertalingen",
                        "fields": {
                            "example": examplepair["example"],
                            "translation": examplepair["translation"],
                            "link": link,
                        },
                        "options": {
                            "allowDuplicate": False,
                            "duplicateScope": "deck",
                            "duplicateScopeOptions": {
                                "deckName": "Nederlands",
                                "checkChildren": False,
                                "checkAllModels": False
                            }
                        },
                        "tags": [
                            "DutchExample"
                        ]
                    }
                }
                try:
                    flashcard = invoke("addNote", **params)
                    print("+1 Example card")
                except Exception as e:
                    print(f"Example flashcard gen failed: {e}")
            
            if Redirects:
                print("\nRedirects:")
                for redirect in Redirects:
                    print(f"Try \"{redirect["Word"]}\" of type \"{redirect["Type"]}\" instead")

        word = input("\nEnter 123 to exit \nEnter word: ")

def main():
    if not wait_for_anki():
        return
    check_setup()
    mainloop()

if __name__ == "__main__":
    main()