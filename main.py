# -*- coding: utf-8 -*-
"""
main.py
=========
Pika hyrëse e programit. Përdorimi:

  # 1) Trajno modelet mbi TË GJITHË datasetin (bëhet 1 herë, ose kur
  #    dataseti përditësohet)
  python main.py train

  # 2) Gjenero raport PDF për 1 pacient specifik (nga ID në dataset)
  python main.py predict --id 135

  # 3) Gjenero raporte PDF për shumë pacientë njëherësh (batch)
  python main.py predict --ids 135,151,43

  # 4) Gjenero raporte për një kampion të rastësishëm prej N pacientësh
  #    (p.sh. për demonstrim -- MOS e bëj këtë për gjithë 22,000+ pacientë
  #    menjëherë, do marrë kohë/hapësirë; bëje me batch-e)
  python main.py predict --sample 10
"""
import argparse
import sys
import pandas as pd

from src import config, data_loader, synthetic_demo, clinical_rules
from src import train_models, predict_patient, diet_plan, generate_pdf


def cmd_train():
    print("Duke trajnuar modelet mbi të gjithë datasetin...\n")
    train_models.train_all()


def _load_patient_row(patient_id, labeled_df):
    row = labeled_df[labeled_df["PATIENT_ID"] == patient_id]
    if row.empty:
        print(f"[GABIM] Pacienti me ID={patient_id} nuk u gjet në dataset.")
        return None
    return row.iloc[0]


def _generate_report_for_row(row, models, encoders, medians):
    biochem = {c: row.get(c) for c in train_models.FEATURE_COLS if c not in
               ("MOSHA", "BMI")}
    demo = {
        "MOSHA": int(row["MOSHA"]), "GJINIA": row["GJINIA"],
        "NACIONALITETI": row["NACIONALITETI"], "PESHA_KG": row["PESHA_KG"],
        "GJATESIA_CM": row["GJATESIA_CM"], "BMI": row["BMI"],
    }
    patient_input = {**biochem, "MOSHA": demo["MOSHA"], "GJINIA": demo["GJINIA"],
                      "BMI": demo["BMI"]}

    predictions = predict_patient.predict_patient(patient_input, models, encoders, medians)
    diet = diet_plan.build_diet_plan(demo, predictions)

    out_path = f"{config.PATHS['reports_dir']}/raport_pacienti_{int(row['PATIENT_ID'])}.pdf"
    generate_pdf.build_patient_pdf(out_path, int(row["PATIENT_ID"]), biochem, demo,
                                    predictions, diet)
    return out_path


def cmd_predict(ids=None, sample=None):
    print("Duke ngarkuar dataset-in dhe modelet...")
    _, usable = data_loader.load_and_prepare()
    demo = synthetic_demo.generate_for_patients(usable["PATIENT_ID"].tolist())
    merged = usable.merge(demo, on="PATIENT_ID", how="left")
    labeled = clinical_rules.add_all_labels(merged)

    models, encoders, medians = predict_patient.load_models()

    if sample:
        target_rows = labeled.sample(n=min(sample, len(labeled)),
                                       random_state=config.RANDOM_SEED)
    else:
        target_rows = labeled[labeled["PATIENT_ID"].isin(ids)]
        missing = set(ids) - set(target_rows["PATIENT_ID"])
        for m in missing:
            print(f"[GABIM] Pacienti ID={m} nuk u gjet.")

    generated = []
    for _, row in target_rows.iterrows():
        path = _generate_report_for_row(row, models, encoders, medians)
        print(f"  -> Raporti u krijua: {path}")
        generated.append(path)

    print(f"\nGjithsej {len(generated)} raporte u gjeneruan në '{config.PATHS['reports_dir']}/'.")
    return generated


def cmd_stats(out_path="output/statistika_te_gjithe_pacienteve.csv"):
    """
    Eksporton NJË tabelë të vetme (CSV) me demografi + antropometri +
    parashikime për TË GJITHË pacientët -- për analizë statistikore/
    hulumtuese (jo raporte individuale PDF).
    """
    print("Duke ngarkuar dataset-in e plotë dhe duke bërë parashikime vektorizuara...")
    _, usable = data_loader.load_and_prepare()
    demo = synthetic_demo.generate_for_patients(usable["PATIENT_ID"].tolist())
    merged = usable.merge(demo, on="PATIENT_ID", how="left")
    labeled = clinical_rules.add_all_labels(merged)

    models, encoders, medians = predict_patient.load_models()
    full = predict_patient.batch_predict_all(labeled, models, encoders, medians)

    cols_out = [
        "PATIENT_ID", "MOSHA", "GJINIA", "NACIONALITETI", "PESHA_KG",
        "GJATESIA_CM", "BMI", "GLIKEMIA", "HBA1C", "HOLESTEROL", "LDL", "HDL",
        "TRIGLICERIDI", "SIND_METABOLIKE_PARASHIKIM", "DIABET_PARASHIKIM",
        "DIABET_AFERSIA_%", "HIPERTENSION_PARASHIKIM", "LIPID_PARASHIKIM",
    ]
    full[cols_out].to_csv(out_path, index=False)
    print(f"U ruajt: {out_path}  ({len(full)} pacientë)")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sistem ML për parametra biokimikë")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("train", help="Trajno modelet mbi gjithë datasetin")
    sub.add_parser("stats", help="Eksporto CSV statistikor për TË GJITHË pacientët (hulumtim)")

    p_predict = sub.add_parser("predict", help="Gjenero raport(e) PDF për pacient(ë)")
    p_predict.add_argument("--id", type=int, help="ID i një pacienti")
    p_predict.add_argument("--ids", type=str, help="ID të shumtë, të ndara me presje")
    p_predict.add_argument("--sample", type=int, help="Gjenero për N pacientë të rastësishëm")

    args = parser.parse_args()

    if args.command == "train":
        cmd_train()
    elif args.command == "stats":
        cmd_stats()
    elif args.command == "predict":
        if args.id:
            cmd_predict(ids=[args.id])
        elif args.ids:
            cmd_predict(ids=[int(x) for x in args.ids.split(",")])
        elif args.sample:
            cmd_predict(sample=args.sample)
        else:
            print("Specifiko --id, --ids, ose --sample")
            sys.exit(1)
    else:
        parser.print_help()
