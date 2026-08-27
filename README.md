# Sistem ML për Parametra Biokimikë — Parashikim i Sindromës Metabolike, Diabetit, Hipertensionit & Planit Ushqimor

## 1. Çfarë bën programi

Bazuar mbi dataset-in real me analiza laboratorike (33,876 pacientë, ~30,000
"të përdorshëm"), programi:

1. **Pastron dhe grumbullon** të dhënat e egra (CSV me encoding CP1251, presje
   decimale, vlera "të egra" si `>75,000`, `da se povt`, etj.)
2. **Trajnon 4 modele Random Forest** mbi TË GJITHË datasetin:
   - Sindroma Metabolike → `Low` / `Medium` / `High`
   - Rreziku i Diabetit → `Normal` / `Prediabet` / `Diabetik` + % afërsie
   - Hipertensioni → `Normal` / `Kufitar` / `I lartë`
   - Profili Lipidik → `Normal` / `Kufitar` / `I lartë`
3. **Gjeneron raporte PDF individuale** për çdo pacient (biokimi + demografi +
   antropometri + parashikime + plan ushqimor i personalizuar)
4. **Eksporton statistika për të gjithë popullsinë** (CSV) për analizë
   kërkimore/statistikore (pika 2 & 3 e kërkesës sate)

## 2. ⚠️ SUPOZIME TË RËNDËSISHME (duhen lexuar!)

| Çka | Statusi | Shpjegim |
|---|---|---|
| **Parametrat biokimikë** | ✅ REALE | Nga dataseti yt origjinal |
| **Mosha, Gjinia, Nacionaliteti** | ⚠️ SINTETIKE | Dataseti origjinal NUK i ka. Gjenerohen automatikisht (deterministike, bazuar në ID) VETËM për prototip. |
| **Pesha, Gjatësia, BMI** | ⚠️ SINTETIKE | Njësoj si më lart. |
| **Presioni i gjakut (tensioni)** | ⚠️ SINTETIK | Nevojitet për hipertension, s'ekziston fare në dataset -- gjenerohet i rastësishëm (i lidhur lehtë me moshën). Për këtë arsye modeli i hipertensionit ka saktësi të ulët (~46%) -- kjo ËSHTË E PRITSHME dhe do të rregullohet vetvetiu kur të shtosh presion REAL. |
| **Perimetri i belit** | ❌ Mungon | Kritere NCEP ATP III për sindromën metabolike normalisht kërkojnë bel, jo BMI -- kemi përdorur BMI≥30 si proxy. Shënohet qartë në kod (`config.py`). |

### Si të zëvendësosh të dhënat sintetike me reale

Kur të kesh një dataset të dytë (Excel/CSV) me kolona si `PATIENT_ID, MOSHA,
GJINIA, NACIONALITETI, PESHA_KG, GJATESIA_CM` (ndoshta edhe presion real):

1. Hap `src/synthetic_demo.py`
2. Zëvendëso funksionin `generate_for_patients()` me një funksion që lexon
   Excel-in tënd dhe bën `merge` me `PATIENT_ID`
3. Asgjë tjetër në program NUK ndryshon -- pjesa tjetër (trajnimi, PDF,
   statistikat) punon automatikisht me të dhënat e reja

## 3. Struktura e projektit

```
biochem_ml/
├── main.py                  <- pika hyrëse (CLI)
├── requirements.txt
├── src/
│   ├── config.py             <- pragjet klinike, emrat e kolonave
│   ├── data_loader.py        <- ngarkim + pastrim CSV real
│   ├── synthetic_demo.py     <- demografi/antropometri (SINTETIKE -- shiko lart)
│   ├── clinical_rules.py     <- kriteret klinike (NCEP ATP III, ADA, ESC/ESH)
│   ├── train_models.py       <- trajnimi i 4 modeleve ML
│   ├── predict_patient.py    <- parashikim për 1 pacient / batch
│   ├── diet_plan.py          <- plani ushqimor i personalizuar
│   └── generate_pdf.py       <- gjenerimi i raportit PDF
├── models/                   <- modelet e trajnuara (.pkl) -- krijohen nga `train`
├── data/                     <- të dhëna të pastruara/etiketuara (parquet)
├── reports/                  <- raportet PDF individuale
├── output/                   <- eksporti statistikor CSV
└── dashboard/                <- Dashboard Interaktiv (Streamlit)
    ├── app.py                 <- faqja kryesore + "Përmbledhje e Popullsisë"
    ├── data_service.py        <- ngarkim/cache i të dhënave & modeleve
    ├── page_patient.py        <- faqja "Profili i Pacientit"
    ├── page_compare.py        <- faqja "Krahasime & Filtra"
    └── page_export.py         <- faqja "Eksport Batch"
```

## 4. 🖥️ Dashboard Interaktiv (Streamlit)

Përveç CLI-t (`main.py`), ekziston edhe një **dashboard web interaktiv** në
dosjen `dashboard/`, i ndërtuar me Streamlit + Plotly.

### Nisja

```bash
pip install -r requirements.txt
cd dashboard
streamlit run app.py
```

Hapet automatikisht në shfletues, zakonisht në `http://localhost:8501`.

### Faqet e dashboard-it

1. **📊 Përmbledhje e Popullsisë** — KPI karta, histograme, pie charts për
   demografi/BMI, shpërndarja e 4 kategorive kryesore të riskut, filtra
   globale (gjini, nacionalitet, moshë) në sidebar, scatter BMI↔Glikemia.
2. **🧑‍⚕️ Profili i Pacientit** — kërko sipas ID, shiko biokiminë, gauge
   charts për të 4 parashikimet, planin ushqimor interaktiv (pie chart
   makronutrientësh), dhe **shkarko PDF-në e gjeneruar live** me një klik.
3. **🔍 Krahasime & Filtra** — filtro popullsinë sipas disa dimensioneve
   njëherësh, krahaso grupe (bar charts, box plots), eksporto nën-grupin
   e filtruar si CSV.
4. **📁 Eksport Batch** — gjenero shumë raporte PDF njëherësh (sipas ID-ve
   specifike, kampion i rastësishëm, ose sipas kategorisë së riskut) dhe
   shkarko si **ZIP**; ose eksporto statistikat e plota (30,000+ pacientë)
   si CSV.

### Shënim teknik

Dashboard-i përdor `dashboard/data_service.py` për të ngarkuar/cache-uar
modelet dhe të dhënat (`@st.cache_resource` / `@st.cache_data`), kështu
hapja e parë merr disa sekonda (ose ~1 min nëse `data/patients_full_predicted.parquet`
nuk ekziston ende dhe duhet rillogaritur), më pas çdo ndërveprim është i
shpejtë.

## 5. Si të përdoret (CLI)

```bash
pip install -r requirements.txt

# Hapi 1: Trajno modelet mbi TË GJITHË datasetin (bëhet 1 herë)
python main.py train

# Hapi 2a: Raport PDF për 1 pacient specifik
python main.py predict --id 135

# Hapi 2b: Raporte për disa pacientë njëherësh
python main.py predict --ids 135,151,43,84

# Hapi 2c: Raporte për kampion të rastësishëm (demonstrim, p.sh 10 pacientë)
python main.py predict --sample 10

# Hapi 3: Eksporto statistika për TË GJITHË popullsinë (CSV, për kërkim)
python main.py stats
```

## 6. Përgjigje e drejtpërdrejtë pyetjes: "një nga një apo gjithë dataseti?"

- **Trajnimi (`train`)**: bëhet MBI GJITHË datasetin, një herë (ose kur
  dataseti përditësohet me pacientë të rinj).
- **Parashikimi për PDF individual (`predict`)**: bëhet PACIENT PAS PACIENTI
  (ose në grupe të vogla) sepse çdo PDF është një dokument më vete.
- **Statistikat (`stats`)**: bëhet MBI GJITHË popullsinë njëherësh (vektorizuar,
  disa sekonda për 30,000 pacientë) sepse rezultati është 1 tabelë e vetme.

## 7. Kufizime & çka duhet përmirësuar më vonë

- Zëvendëso demografinë/antropometrinë sintetike me reale (shih §2)
- Nëse ke presion gjaku REAL, hiqe gjenerimin sintetik në `synthetic_demo.py`
  dhe përdore presionin real -- do rrisë ndjeshëm saktësinë e hipertensionit
- Verifiko njësitë (mmol/L supozohet; nëse dataseti ka mg/dL, ndrysho
  `UNITS_ARE_MMOL_L` në `config.py`)
- Emrat e disa kolonave (p.sh. `Nа`, `Т3`, `Т4`) u rikonstruktuan nga encoding
  i thyer -- verifiko me laboratorin origjinal nëse janë 100% korrekte
- Modelet e diabetit/lipideve kanë saktësi shumë të lartë (~100%) sepse
  etiketat vijnë direkt nga vetë glukoza/HbA1c/lipidet -- kjo është e
  qëllimshme (modeli "mëson" pragjet klinike + vlerëson mirë edhe kur mungon
  ndonjë analizë specifike, duke u mbështetur në analizat e tjera të lidhura)

## 8. Përgjegjësia mjekësore

Ky program është për qëllime **edukativo-kërkimore**. Rezultatet NUK
zëvendësojnë diagnozën apo këshillën e mjekut/nutricionistit. Çdo vendim
mjekësor real duhet konsultuar me profesionist të licencuar.
