# BoltKurjerSkolaProject
Autori: Aleksandr and Valera

Android lietotne saziņai ar Arduino, izmantojot Bluetooth
Projekta apraksts
Šī projekta mērķis ir izveidot Android lietotni, kas apstrādā informāciju telefonā un nosūta rezultātus uz Arduino Uno ar HM-10 Bluetooth Low Energy (BLE) moduļa starpniecību. Arduino saņemto tekstu attēlo LCD ekrānā ar I²C savienojumu.
Pašlaik lietotne ir paredzēta teksta nosūtīšanai un Python loģikas integrēšanas izmēģināšanai. Nākamais projekta posms ir telefona kameras un mākslīgā intelekta izmantošana, lai noteiktu cilvēkus un šķēršļus.
Izmantotās tehnoloģijas
- Android Studio un Kotlin — lietotnes saskarne, Bluetooth savienojums un Android funkcijas.
- Chaquopy un Python — Python koda izpilde Android lietotnē un tā rezultātu nodošana Kotlin daļai.
- Bluetooth Low Energy (BLE) — bezvadu datu pārraide starp telefonu un HM-10 moduli.
- Arduino Uno — no Bluetooth moduļa saņemto datu apstrāde.
- I²C LCD — saņemto ziņojumu attēlošana.
- OpenCV / NumPy — bibliotēkas, kas paredzētas turpmākai attēlu apstrādei.
Darbības princips
1. Android lietotne izveido BLE savienojumu ar HM-10 moduli.
2. Lietotājs ievada tekstu vai tiek palaista telefonā esoša Python loģika.
3. Kotlin daļa iegūst nosūtāmo rezultātu un pārsūta to pa Bluetooth.
4. HM-10 nodod datus Arduino, kas tos parāda LCD ekrānā.
Datu plūsma: Android (Kotlin + Python) → BLE → HM-10 → Arduino Uno → I²C LCD
Python kods darbojas telefonā, nevis Arduino. Uz Arduino tiek sūtīts tikai apstrādes rezultāts, piemēram, Hello, STOP vai OBSTACLE.
Bluetooth savienojums
Projektā izmantotais HM-10 tipa modulis atbalsta BLE. Savienojumam tiek izmantoti moduļa piedāvātie pakalpojumi un rakstīšanai piemērotā raksturlieluma UUID. Konkrētais UUID ir jāpārbauda attiecīgajam modulim, jo dažādām versijām tas var atšķirties.
Android lietotnei nepieciešamas atbilstošas Bluetooth atļaujas; to prasības atšķiras atkarībā no Android versijas.
Python integrācija
Python integrācijai tiek izmantots Chaquopy, kas ļauj Kotlin kodam izsaukt Python funkcijas vienas Android lietotnes ietvaros. Tas dod iespēju vēlāk pievienot sarežģītāku datu apstrādi, nemainot galveno saziņas principu ar Arduino.
Vienkāršs paredzētās darbības piemērs:
def process_text(text):
    return text
Funkcijas atgrieztā vērtība tiek nodota Kotlin daļai, kas to nosūta uz Arduino. Python print() izvade pati par sevi netiek automātiski pārsūtīta pa Bluetooth — tā ir atsevišķi jāiegūst vai jāizmanto funkcijas atgrieztā vērtība.
Turpmākā attīstība
Plānots pievienot telefona kameras attēlu apstrādi ar YOLO objektu noteikšanas modeli un vēlāk arī NCNN izpildvidi, ja tā būs saderīga ar izvēlēto Android integrācijas risinājumu.
Paredzētās funkcijas:
- Cilvēka noteikšana un komandas STOP nosūtīšana, ja cilvēks atrodas ierīces kustības ceļā.
- Šķēršļu noteikšana un komandas OBSTACLE nosūtīšana.
- Objektu atrašanās vietas noteikšana attēlā, lai atšķirtu šķēršļus kustības ceļā no objektiem ārpus tā.
- Brīvās vietas un pagriezienu noteikšana skolas gaiteņos.
Šīs ir plānotās, nevis jau pilnībā ieviestās funkcijas. Objektu noteikšanai papildus būs vajadzīga kustības ceļa un attāluma novērtēšanas loģika.
Projekta statuss
Ir izstrādāta Android lietotnes BLE teksta pārraides pieeja un sākta Python integrācija ar Chaquopy. Python bibliotēku instalēšana ir izdevusies, taču pēdējā zināmā kompilēšanas posmā radās Java un Kotlin JVM mērķversiju neatbilstība (Java 11 / Kotlin 17). Pirms Python un mākslīgā intelekta funkciju izmantošanas gatavā lietotnē šī kļūda jānovērš un viss datu pārraides cikls jāpārbauda ierīcē.

# Autonomā robota šķēršļu un pagriezienu noteikšanas sistēma

## Projekta apraksts

Šī projekta mērķis ir izstrādāt datorredzes sistēmu, kas palīdz autonomam robotam pārvietoties skolas gaiteņos, atpazīt šķēršļus, noteikt brīvos pārvietošanās virzienus un identificēt iespējamos pagriezienus.

Sistēma sastāv no diviem Python moduļiem:
- `test.py` — objektu atpazīšana un šķēršļu apiešanas virziena noteikšana.
- `turn_detection.py` — pagriezienu un brīvās vietas noteikšana pa kreisi, pa labi un taisni.

Abi moduļi izmanto kameras attēlus, taču to darbības principi atšķiras.

## 1. Objektu un šķēršļu noteikšana — test.py

Šajā modulī tiek izmantots YOLO26n mākslīgā intelekta modelis, lai atpazītu objektus kameras attēlā un noteiktu, vai tie traucē robota kustībai.

### Darbības princips

1. Programma saņem attēlu no kameras.
2. YOLO modelis identificē objektus, nosaka to klasi, koordinātas un atpazīšanas ticamību.
3. Tiek izveidota trapecveida zona, kas aptuveni atbilst robota paredzētajam kustības ceļam.
4. Šī zona tiek sadalīta trīs daļās: kreisajā, centrālajā un labajā.
5. Programma aprēķina, cik liela katra objekta ierobežojošā taisnstūra daļa pārklājas ar attiecīgo zonu.
6. Atkarībā no aizņemtajām zonām programma nosaka iespējamo šķēršļa apiešanas virzienu.

### Rezultāti

Programma atgriež informāciju par atpazītajiem objektiem, to koordinātām un kustības zonu stāvokli.

Iespējamās `avoidance` vērtības:

| Vērtība | Nozīme |
|---|---|
| `not_needed` | Centrālā zona ir brīva |
| `left` | Šķērsli iespējams apbraukt pa kreisi |
| `right` | Šķērsli iespējams apbraukt pa labi |
| `left_or_right` | Abas sānu zonas ir brīvas |
| `nowhere` | Visas trīs zonas ir aizņemtas |

## 2. Pagriezienu noteikšana — turn_detection.py

Šis modulis paredzēts iespējamo pagriezienu un brīvo pārvietošanās virzienu noteikšanai. Atšķirībā no pirmā moduļa tas neizmanto YOLO, bet analizē attēla kontūras un tekstūru ar OpenCV palīdzību.

Moduli paredzēts aktivizēt tikai tad, kad robots saskaņā ar navigācijas informāciju tuvojas gaidāmajam krustojumam.

### Darbības princips

1. Kameras attēls tiek samazināts, lai paātrinātu apstrādi.
2. Attēls tiek pārveidots pelēktoņos, uzlabots tā kontrasts un noteiktas kontūras, izmantojot Canny algoritmu.
3. Attēls tiek sadalīts kreisajā, centrālajā un labajā zonā.
4. Katrā zonā tiek analizēta kontūru koncentrācija tuvākajā un tālākajā attēla daļā.
5. Papildus tiek analizēta attēla tekstūra, lai samazinātu iespēju sajaukt gludu sienu ar brīvu telpu.

### Rezultātu stabilizēšana

Lai samazinātu kļūdainu noteikšanas gadījumu skaitu, `TurnDetector` klase analizē vairākus secīgus kameras kadrus un ņem vērā ar odometriju izmērīto nobraukto attālumu.

Lēmuma ticamības pārbaudei nepieciešami vismaz trīs secīgi vienādi rezultāti un minimālais nobrauktais attālums. Gala rezultāts tiek aprēķināts no saglabātajiem novērojumiem.

Programma atgriež trīs loģiskās vērtības:

- `Left` — vai kreisais virziens ir novērtēts kā brīvs.
- `Right` — vai labais virziens ir novērtēts kā brīvs.
- `Forward` — vai kustību iespējams turpināt taisni.

Vērtība `True` apzīmē virzienu, kuru algoritms novērtējis kā brīvu, bet `False` — virzienu, kas nav atzīts par brīvu.

## 3. Nepieciešamās bibliotēkas

Programmu darbībai nepieciešams Python un šādas bibliotēkas:

- `ultralytics` — YOLO modeļa izmantošanai.
- `opencv-python` — attēlu apstrādei.
- `numpy` — skaitliskajiem aprēķiniem.

Bibliotēkas var instalēt ar komandu:

```bash
pip install ultralytics opencv-python numpy
```

## 4. Programmu testēšana

**Objektu noteikšana**

Failam `test.py` nepieciešams modelis `yolo26n.pt` un pārbaudes attēls `image.png`.

```bash
python test.py
```

Programma terminālī parāda noteiktos objektus, aizņemtās kustības zonas un iespējamo šķēršļa apiešanas virzienu.

**Pagriezienu noteikšana**

Failu `turn_detection.py` var pārbaudīt ar attēlu `turn.jpg`:

```bash
python turn_detection.py turn.jpg
```

Programma parāda katra virziena novērtējumu un saglabā vizualizāciju failā `debug_turn.jpg`.

Viena attēla pārbaude ir paredzēta tikai algoritma sākotnējai testēšanai. Reālā kustībā jāizmanto `TurnDetector` klase ar secīgiem kameras kadriem un odometrijas datiem.

## 5. Turpmākā attīstība

Nākamais projekta posms ir abu moduļu integrācija kopējā navigācijas sistēmā, lai robots varētu noteikt šķēršļus un izvēlēties piemērotu pārvietošanās virzienu. Paredzēts, ka attēlu apstrāde notiks Android tālrunī, savukārt vadības komandas tiks nosūtītas Arduino mikrokontrollerim, izmantojot HM-10 Bluetooth moduli.

**Svarīgi:** pašreizējie algoritmi ir eksperimentāli. Tie novērtē brīvo vietu pēc kameras attēla, bet neveic precīzus attāluma mērījumus un negarantē drošu pārvietošanās ceļu. Pirms autonomas izmantošanas nepieciešama papildu testēšana reālā vidē.
