"""성능 기록을 cb_model_version_v1 에 남긴다.

2026-09-01 에 MODEL_VERSION 을 주지 않아 v1.0.0 행이 14문항 평가 결과로 덮였다.
그래서 model_version 은 필수이고, 기존 행이 있으면 force 없이 덮지 않는다.
"""

INSERT = """INSERT INTO cb_model_version_v1
  (model_version, family, question_set_version, macro_f1, high_burden_recall,
   undecidable_rate, activated_at, deactivated_at, notes)
  VALUES (%s,%s,%s,%s,%s,%s,NOW(),NULL,%s)
  ON DUPLICATE KEY UPDATE family=VALUES(family), macro_f1=VALUES(macro_f1),
    high_burden_recall=VALUES(high_burden_recall),
    undecidable_rate=VALUES(undecidable_rate),
    activated_at=NOW(), deactivated_at=NULL, notes=VALUES(notes)"""


def write(conn, model_version, family, qset, f1, rec, und, notes, force=False):
    if not model_version:
        raise ValueError(
            'model_version 은 필수입니다. 생략하면 다른 버전의 기록을 덮어씁니다')

    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM cb_model_version_v1 WHERE model_version = %s',
                (model_version,))
    if cur.fetchone()[0] and not force:
        raise ValueError(
            f'{model_version} 기록이 이미 있습니다. 덮어쓰려면 --force 를 주세요')

    cur.execute('UPDATE cb_model_version_v1 SET deactivated_at = NOW() '
                'WHERE deactivated_at IS NULL')
    cur.execute(INSERT, (model_version, family, qset, round(f1, 4), round(rec, 4),
                         round(und, 4), notes))
    conn.commit()
