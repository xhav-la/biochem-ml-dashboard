-- ============================================================
-- Skema Supabase per klientet e nutricionistit ("Pacient i Ri")
-- Ekzekuto kete te Supabase -> SQL Editor -> New query -> Run
-- ============================================================

create table if not exists klientet (
    id bigint generated always as identity primary key,
    emri text not null,
    krijuar_me timestamptz not null default now(),

    -- Demografia & Antropometria (REALE, futur nga nutricionisti)
    mosha integer not null,
    gjinia text not null,
    nacionaliteti text,
    pesha_kg numeric not null,
    gjatesia_cm numeric not null,
    bmi numeric not null,
    tension_sistolik numeric,
    tension_diastolik numeric,

    -- Parametrat biokimike (te gjitha opsionale -- mund te mungojne)
    glikemia numeric,
    hba1c numeric,
    holesterol numeric,
    ldl numeric,
    hdl numeric,
    trigliceridi numeric,
    hemoglobin numeric,
    hematokrit numeric,
    trombociti numeric,
    albumini numeric,
    totalni_proteini numeric,
    crp numeric,
    na numeric,
    mg numeric,
    fe numeric,
    tsh numeric,
    ft4 numeric,

    -- Rezultatet e parashikimeve (ruajtur si JSON per fleksibilitet)
    predictions jsonb,
    diet jsonb
);

-- Indeks per kerkim te shpejte sipas emrit/kohes
create index if not exists idx_klientet_krijuar_me on klientet (krijuar_me desc);
create index if not exists idx_klientet_emri on klientet (emri);

-- Row Level Security: e mbajme te thjeshte (akses vetem permes backend-it
-- tone qe perdor "service_role" key, jo publik nga shfletuesi)
alter table klientet enable row level security;

-- Komenti i nutricionistit/dietologut (shtuar më vonë).
-- Nëse tabela ekziston tashmë, mjafton të ekzekutosh VETËM këtë rresht:
alter table klientet add column if not exists koment_nutricionisti text;

-- ============================================================
-- PLANET USHQIMORE (faqja "Plani Ushqimor (Dietologu)")
-- ============================================================
create table if not exists planet_ushqimore (
    id bigint generated always as identity primary key,
    krijuar_me timestamptz not null default now(),
    klient_id bigint references klientet(id) on delete set null,
    emri text not null,
    titulli text not null,
    data_fillimit date,
    data_mbarimit date,
    permbajtja jsonb not null
);
create index if not exists idx_planet_emri on planet_ushqimore (emri);
alter table planet_ushqimore enable row level security;
