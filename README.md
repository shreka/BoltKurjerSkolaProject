# BoltKurjerSkolaProject
Autori: Aleksandr and Valera
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
