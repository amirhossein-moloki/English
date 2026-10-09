# AnkiConnect Configuration & Note Model Setup

## AnkiConnect Setup
1. Open Anki.
2. Go to `Tools` -> `Add-ons`.
3. Click `Get Add-ons...`, enter code `2055492153` (AnkiConnect), and restart Anki.
4. Ensure AnkiConnect is listening at `http://localhost:8765`.

## Note Model Structure: "English Vocabulary"
The application automatically manages the note type `English Vocabulary` via AnkiConnect.

### Note Model Fields:
- `Word`: Target English word or phrase
- `IPA`: Pronunciation in IPA
- `PartOfSpeech`: Grammatical category (e.g. adjective, verb, noun)
- `Meaning_EN`: Concise English definition
- `Meaning_FA`: Natural Persian translation
- `Example_EN`: English usage example sentence
- `Example_FA`: Persian translation of example
- `Collocations`: Comma-separated collocations
- `Synonyms`: Comma-separated synonyms
- `Antonyms`: Comma-separated antonyms
- `Notes`: Grammar, register, or usage notes
- `Audio`: `[sound:filename.mp3]` reference
- `Source`: Origin source metadata
- `Tags`: Space-separated tags
- `Meaning`: Legacy fallback field
- `Example`: Legacy fallback field
- `Pronunciation`: Legacy fallback field

### Card Templates

#### Card Type A — English Recognition
- **Front**:
  ```html
  <div class="card front">
    <h1 class="word">{{Word}}</h1>
    {{#Audio}}<div class="audio">{{Audio}}</div>{{/Audio}}
  </div>
  ```
- **Back**:
  ```html
  <div class="card back">
    <h1 class="word">{{Word}}</h1>
    <div class="pos"><i>{{PartOfSpeech}}</i> {{#IPA}}[{{IPA}}]{{/IPA}}</div>
    <hr>
    {{#Meaning_EN}}<div class="meaning-en"><b>EN:</b> {{Meaning_EN}}</div>{{/Meaning_EN}}
    {{#Meaning_FA}}<div class="meaning-fa" dir="rtl"><b>FA:</b> {{Meaning_FA}}</div>{{/Meaning_FA}}
    <hr>
    {{#Example_EN}}<div class="example-en"><b>Example:</b> {{Example_EN}}</div>{{/Example_EN}}
    {{#Example_FA}}<div class="example-fa" dir="rtl"><b>ترجمه:</b> {{Example_FA}}</div>{{/Example_FA}}
    {{#Collocations}}<div class="collocations"><b>Collocations:</b> {{Collocations}}</div>{{/Collocations}}
    {{#Audio}}<div class="audio">{{Audio}}</div>{{/Audio}}
    <div class="source"><small>Source: {{Source}}</small></div>
  </div>
  ```

#### Card Type B — Active Recall
- **Front**:
  ```html
  <div class="card front active-recall">
    <div class="prompt"><b>Recall English Word:</b></div>
    {{#Meaning_FA}}<div class="meaning-fa" dir="rtl"><h2 dir="rtl">{{Meaning_FA}}</h2></div>{{/Meaning_FA}}
    {{^Meaning_FA}}<div class="meaning-en"><h2>{{Meaning_EN}}</h2></div>{{/Meaning_FA}}
    {{#Example_FA}}<div class="example-fa" dir="rtl"><i>"{{Example_FA}}"</i></div>{{/Example_FA}}
    {{#PartOfSpeech}}<div class="pos">({{PartOfSpeech}})</div>{{/PartOfSpeech}}
  </div>
  ```
- **Back**:
  ```html
  <div class="card back active-recall">
    <h1 class="word">{{Word}}</h1>
    <div class="pos"><i>{{PartOfSpeech}}</i> {{#IPA}}[{{IPA}}]{{/IPA}}</div>
    {{#Audio}}<div class="audio">{{Audio}}</div>{{/Audio}}
    <hr>
    {{#Meaning_EN}}<div class="meaning-en"><b>EN:</b> {{Meaning_EN}}</div>{{/Meaning_EN}}
    {{#Meaning_FA}}<div class="meaning-fa" dir="rtl"><b>FA:</b> {{Meaning_FA}}</div>{{/Meaning_FA}}
    {{#Example_EN}}<div class="example-en"><b>Example:</b> {{Example_EN}}</div>{{/Example_EN}}
  </div>
  ```
