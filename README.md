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
3. **➕ Pacient i Ri** — **për nutricionistin/mjekun**: formular ku futen ME
   DORË të dhënat REALE (jo sintetike) të një klienti të ri -- emër/ID,
   moshë, gjini, nacionalitet, peshë, gjatësi, tension (opsional), dhe
   analizat biokimike që i ka bërë (fushat që mungojnë lihen 0 → trajtohen
   si "mungon", parashikimi bazohet te analizat e tjera). Rezultati: gauge
   charts, plan ushqimor, PDF live -- njësoj si për pacientët nga dataseti.
   Klientët e futur gjatë sesionit shfaqen në një tabelë historiku (me
   eksport CSV/ZIP), por **RUHEN VETËM PËR SESIONIN AKTIV** -- shih
   kufizimin më poshtë.
4. **🔍 Krahasime & Filtra** — filtro popullsinë sipas disa dimensioneve
   njëherësh, krahaso grupe (bar charts, box plots), eksporto nën-grupin
   e filtruar si CSV.
5. **📁 Eksport Batch** — gjenero shumë raporte PDF njëherësh (sipas ID-ve
   specifike, kampion i rastësishëm, ose sipas kategorisë së riskut) dhe
   shkarko si **ZIP**; ose eksporto statistikat e plota (30,000+ pacientë)
   si CSV.

### 🗄️ Ruajtje e Përhershme e Klientëve (Supabase, FALAS)

Faqja "➕ Pacient i Ri" mbështet ruajtje TË PËRHERSHME të klientëve përmes
[Supabase](https://supabase.com) (PostgreSQL falas). Pa këtë konfigurim,
klientët ruhen vetëm për sesionin aktiv (fshihen kur rifreskon faqen).

#### Konfigurimi (bëhet 1 herë)

1. Krijo llogari/projekt falas te [supabase.com](https://supabase.com)
2. Te **SQL Editor**, ekzekuto skriptin `supabase_setup.sql` (është te rrënja
   e këtij projekti) -- krijon tabelën `klientet`
3. Te **Project Settings → API**, merr **Project URL** dhe **service_role key**
4. Shtoji te `.streamlit/secrets.toml` (lokalisht) ose te **Secrets** në
   Streamlit Cloud (online):
   ```toml
   supabase_url = "https://xxxxxxxxxxxx.supabase.co"
   supabase_key = "eyJhbGciOi...."
   ```
5. Rinis aplikacionin -- faqja "Pacient i Ri" do të shfaqë "🟢 Baza e të
   dhënave është lidhur"

Pa këtë konfigurim, aplikacioni vazhdon të punojë normalisht (fallback
automatik te ruajtja vetëm-për-sesion) -- asgjë nuk thyhet.

#### Çka mundëson

- Klientët ruhen PËRGJITHMONË (jo vetëm për sesionin)
- Kërkim sipas emrit/ID në historikun e plotë
- Rihapje e çdo klienti të vjetër + rigjenerim PDF pa rifutur analizat
- Fshirje e klientëve individualë
- I arritshëm nga çdo pajisje/sesion (jo vetëm kompjuteri ku u fut)

### Shënim teknik

Dashboard-i përdor `dashboard/data_service.py` për të ngarkuar/cache-uar
modelet dhe të dhënat (`@st.cache_resource` / `@st.cache_data`), kështu
hapja e parë merr disa sekonda (ose ~1 min nëse `data/patients_full_predicted.parquet`
nuk ekziston ende dhe duhet rillogaritur), më pas çdo ndërveprim është i
shpejtë.

## 5. 🌐 Publikimi ONLINE (falas, me Streamlit Community Cloud)

Dashboard-i është i mbrojtur me **fjalëkalim** (shih `dashboard/auth.py`) sepse
përmban të dhëna reale shëndetësore. Ndiq hapat më poshtë me kujdes.

### Hapi 1 — Krijo repo në GitHub

1. Hap [github.com](https://github.com) → krijo llogari (nëse s'ke) → **New repository**
2. Emërto p.sh. `biochem-ml-dashboard`. Mund ta bësh **Private** (Streamlit
   Community Cloud falas lejon 1 repo privat të publikuar) ose **Public** —
   fjalëkalimi mbron aplikacionin gjithsesi, pavarësisht dukshmërisë së kodit.
3. MOS shto README/gitignore automatik (i kemi tashmë).

### Hapi 2 — Ngarko kodin (nga kompjuteri yt, pas unzip)

```bash
cd biochem_ml
git remote add origin https://github.com/USERNAME/biochem-ml-dashboard.git
git push -u origin main
```

*(Zip-i që të dhashë ka tashmë `git init` + commit të parë të bërë —
duhet vetëm `remote add` + `push`.)*

### Hapi 3 — Publiko në Streamlit Community Cloud (FALAS)

1. Shko te [share.streamlit.io](https://share.streamlit.io) → **Sign in with GitHub**
2. **New app** → zgjidh repo-n `biochem-ml-dashboard`, branch `main`
3. **Main file path**: `dashboard/app.py`   ⚠️ (JO `app.py` — është brenda `dashboard/`)
4. **PARA se të klikosh Deploy** (ose menjëherë pas), shko te **Advanced
   settings → Secrets** dhe shto:
   ```toml
   app_password = "zgjidh_nje_fjalekalim_te_forte"
   ```
5. Kliko **Deploy**. Prisni 2-5 minuta (instalon paketat nga `requirements.txt`).
6. Merr linkun tip `https://biochem-ml-dashboard-xxxx.streamlit.app` — ndaje
   VETËM me njerëz të autorizuar (bashkë me fjalëkalimin, veçmas, p.sh. me telefon).

### ⚠️ Shënime të rëndësishme

- **Linku është teknikisht i arritshëm nga kushdo** që e ka (edhe nëse repo është
  privat) — prandaj fjalëkalimi është mbrojtja reale, jo dukshmëria e repo-s.
- Free tier ka **1GB RAM** — modelet tona (~38MB) e kalojnë lehtë këtë limit,
  por nëse shton shumë më shumë të dhëna, mund të duhet upgrade.
- Aplikacionet falas **"flenë" pas ~7 ditësh pa vizitorë** — hapet automatikisht
  (me pak vonesë) në vizitën e parë pas kësaj.
- Për të ndryshuar fjalëkalimin më vonë: Streamlit Cloud → app-i yt → **Settings
  → Secrets** → ndrysho `app_password` → **Save** (rindizet automatikisht).
- Dataseti i etiketuar (`data/patients_full_predicted.parquet`) dhe modelet
  janë PËRFSHIRË në repo (~20MB), kështu online NUK ka nevojë për CSV-në
  origjinale as rillogaritje — hapet menjëherë me modelet e gatshme.

### Testim lokal para publikimit

```bash
# Krijo secrets.toml LOKAL (KURRË mos e commito!)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# hape dhe vendos fjalëkalimin tënd brenda

# NISE NGA RRËNJA E PROJEKTIT (jo nga brenda dashboard/):
streamlit run dashboard/app.py
```

## 6. Si të përdoret (CLI)

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

## 7. Përgjigje e drejtpërdrejtë pyetjes: "një nga një apo gjithë dataseti?"

- **Trajnimi (`train`)**: bëhet MBI GJITHË datasetin, një herë (ose kur
  dataseti përditësohet me pacientë të rinj).
- **Parashikimi për PDF individual (`predict`)**: bëhet PACIENT PAS PACIENTI
  (ose në grupe të vogla) sepse çdo PDF është një dokument më vete.
- **Statistikat (`stats`)**: bëhet MBI GJITHË popullsinë njëherësh (vektorizuar,
  disa sekonda për 30,000 pacientë) sepse rezultati është 1 tabelë e vetme.

## 8. Kufizime & çka duhet përmirësuar më vonë

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

## 9. Përgjegjësia mjekësore

Ky program është për qëllime **edukativo-kërkimore**. Rezultatet NUK
zëvendësojnë diagnozën apo këshillën e mjekut/nutricionistit. Çdo vendim
mjekësor real duhet konsultuar me profesionist të licencuar.
