"""
Cria índice em date_status_dt_iso em todas as collections do banco,
permitindo range queries eficientes ($gte/$lte) em vez de full scan.

Uso:
    python3 scripts_migracao_criar_indices.py --mongo-uri "mongodb://root:SENHA@host" --db status_agent
"""
import argparse

import pymongo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mongo-uri", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--collection", help="Criar índice apenas em uma collection específica")
    args = parser.parse_args()

    client = pymongo.MongoClient(args.mongo_uri)
    db = client[args.db]

    collection_names = [args.collection] if args.collection else db.list_collection_names()

    created = 0
    already_existed = 0

    print(f"Criando índices em {len(collection_names)} collection(s)...")

    for i, name in enumerate(collection_names, start=1):
        collection = db[name]
        existing_indexes = {idx["name"] for idx in collection.list_indexes()}

        if "date_status_dt_iso_1" in existing_indexes:
            already_existed += 1
            continue

        collection.create_index([("date_status_dt_iso", pymongo.ASCENDING)])
        created += 1

        if i % 50 == 0 or i == len(collection_names):
            print(f"[{i}/{len(collection_names)}] processado ({created} criados, {already_existed} já existiam)")

    print(f"\nTotal: {created} índices criados, {already_existed} já existiam.")


if __name__ == "__main__":
    main()
