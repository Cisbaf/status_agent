"""
Script de backfill: popula os campos date_status_dt_iso e last_date_dt_iso
(tipo Date nativo do MongoDB) a partir dos campos legados em string
(date_status_dt, last_date_dt, formato "DD/MM/YYYY, HH:MM:SS").

É idempotente e não destrutivo: só escreve nos documentos que ainda não
possuem os campos _iso, e nunca remove os campos string originais.

Uso:
    python3 scripts_migracao_backfill_iso_dates.py --mongo-uri "mongodb://root:SENHA@host" --db status_agent
    python3 scripts_migracao_backfill_iso_dates.py --mongo-uri "..." --db status_agent --dry-run
"""
import argparse
from datetime import datetime

import pymongo

LEGACY_DATE_FORMAT = "%d/%m/%Y, %H:%M:%S"

# IMPORTANTE sobre timezone:
# Os campos legados (date_status_dt, last_date_dt) já representam o horário
# LOCAL de Brasília/São Paulo (America/Sao_Paulo), sem informação de fuso.
# Os novos campos _iso são gravados como datetime "naive" com os MESMOS
# dígitos de hora/minuto/segundo do valor original — não fazemos nenhuma
# conversão de fuso horário aqui. O MongoDB grava/exibe esse valor rotulado
# como UTC (comportamento padrão do driver ao não receber tzinfo), mas os
# NÚMEROS continuam representando o horário local de Brasília, não um
# instante UTC real. Isso é proposital: as análises precisam do horário
# real do evento em horário de Brasília, não do instante UTC.
#
# Consequência prática: ao consultar por intervalo de datas (ex: no
# relatorios-agentes), os limites do filtro ($gte/$lte) também devem ser
# construídos como horário de Brasília "naive" (sem tzinfo, ou com tzinfo
# removido antes de montar a query), para que a comparação seja consistente
# com o que foi gravado.

FIELD_MAP = {
    "date_status_dt": "date_status_dt_iso",
    "last_date_dt": "last_date_dt_iso",
}


def parse_legacy_date(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, LEGACY_DATE_FORMAT)
    except ValueError:
        return None


def backfill_collection(collection, dry_run: bool = False) -> dict:
    """Retorna estatísticas do backfill para uma collection."""
    stats = {"scanned": 0, "updated": 0, "skipped_already_migrated": 0, "skipped_unparseable": 0}

    # Só busca documentos que ainda não têm pelo menos um dos campos _iso,
    # para tornar reruns rápidos (não reprocessa o que já foi migrado).
    query = {
        "$or": [
            {"date_status_dt_iso": {"$exists": False}},
            {"last_date_dt_iso": {"$exists": False}},
        ]
    }

    bulk_ops = []
    for doc in collection.find(query, {"_id": 1, "date_status_dt": 1, "last_date_dt": 1}):
        stats["scanned"] += 1
        update_fields = {}

        for legacy_field, iso_field in FIELD_MAP.items():
            if iso_field in doc:
                continue
            parsed = parse_legacy_date(doc.get(legacy_field))
            if parsed is not None:
                update_fields[iso_field] = parsed

        if not update_fields:
            if any(f in doc for f in FIELD_MAP.values()):
                stats["skipped_already_migrated"] += 1
            else:
                stats["skipped_unparseable"] += 1
            continue

        bulk_ops.append(
            pymongo.UpdateOne({"_id": doc["_id"]}, {"$set": update_fields})
        )
        stats["updated"] += 1

        if len(bulk_ops) >= 1000:
            if not dry_run:
                collection.bulk_write(bulk_ops, ordered=False)
            bulk_ops = []

    if bulk_ops and not dry_run:
        collection.bulk_write(bulk_ops, ordered=False)

    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mongo-uri", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Não grava nada, só reporta o que seria feito")
    parser.add_argument("--collection", help="Migrar apenas uma collection específica (para testes)")
    args = parser.parse_args()

    client = pymongo.MongoClient(args.mongo_uri)
    db = client[args.db]

    collection_names = [args.collection] if args.collection else db.list_collection_names()

    total_scanned = 0
    total_updated = 0

    print(f"{'[DRY-RUN] ' if args.dry_run else ''}Iniciando backfill em {len(collection_names)} collection(s)...")

    for i, name in enumerate(collection_names, start=1):
        collection = db[name]
        stats = backfill_collection(collection, dry_run=args.dry_run)
        total_scanned += stats["scanned"]
        total_updated += stats["updated"]
        if stats["scanned"] > 0:
            print(
                f"[{i}/{len(collection_names)}] {name}: "
                f"scanned={stats['scanned']} updated={stats['updated']} "
                f"ja_migrados={stats['skipped_already_migrated']} "
                f"nao_parseaveis={stats['skipped_unparseable']}"
            )

    print(f"\nTotal: {total_scanned} documentos verificados, {total_updated} atualizados.")


if __name__ == "__main__":
    main()
