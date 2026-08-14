#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Recria TODA a solução "Databricks Blog Digest" em um ambiente.
#
# Cria: schema + tabelas, notebooks, Legacy SQL query, Legacy SQL alert,
# 1 Notification Destination por destinatário (e-mails OCULTOS), os jobs
# (diário e de envio) e popula a lista. Aplica o template do e-mail no fim.
#
# Pré-requisitos:
#   - Databricks CLI autenticado no workspace alvo (databricks auth login ...)
#   - Um SQL Warehouse (serverless) ligado
#   - python3
#
# Uso:  edite o bloco CONFIG e rode:  bash deploy.sh
# =============================================================================
set -euo pipefail

# ----------------------------- CONFIG ----------------------------------------
PROFILE="fe-vm-cosin-aws-serverless"
CATALOG="cosin_aws_serverless_catalog"
SCHEMA="blog_digest"
WAREHOUSE_ID="0c2def7684630e5e"
USER_PATH="/Workspace/Users/rodrigo.cosin@databricks.com/tools_demos_public/blog_digest"
LLM_ENDPOINT="databricks-claude-opus-4-8"
SEND_CRON="0 0 10 ? * FRI"     # envio: sexta 10:00
DAILY_CRON="0 0 8 * * ?"       # ingestão + sync: 08:00
TIMEZONE="America/Sao_Paulo"
SEED_EMAILS=("rodrigocosin@gmail.com")   # lista inicial (1 destino por e-mail)
SA_NAME="Rodrigo Cosin"                   # SA dono do envio (sync filtra por este sa)
AE_NAME="Rodolfo Catharino"               # AE da conta (cadastro)
# -----------------------------------------------------------------------------
P=(--profile "$PROFILE")
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "==> 1/9 Schema + tabelas"
PROFILE="$PROFILE" WAREHOUSE_ID="$WAREHOUSE_ID" python3 "$HERE/run_sql.py" "$HERE/sql/01_setup_schema.sql"

echo "==> 2/9 Seed de destinatários"
for e in "${SEED_EMAILS[@]}"; do
  PROFILE="$PROFILE" WAREHOUSE_ID="$WAREHOUSE_ID" python3 "$HERE/run_sql.py" -e \
    "INSERT INTO $CATALOG.$SCHEMA.email_recipients (email,name,active,added_at,sa,ae) SELECT '$e','',true,current_timestamp(),'$SA_NAME','$AE_NAME' WHERE NOT EXISTS (SELECT 1 FROM $CATALOG.$SCHEMA.email_recipients WHERE email='$e')"
done

echo "==> 3/9 Upload dos notebooks"
databricks workspace mkdirs "$USER_PATH" "${P[@]}" || true
for nb in 00_preparar_email 01_ingest_and_summarize 02_sync_recipients 03_weekly_log 04_enviar_lotes; do
  databricks workspace import "$USER_PATH/$nb" --file "$HERE/notebooks/$nb.py" \
    --language PYTHON --format SOURCE --overwrite "${P[@]}"
done

echo "==> 4/9 Legacy SQL query"
DS_ID=$(databricks api get /api/2.0/preview/sql/data_sources "${P[@]}" \
  | python3 -c "import json,sys;[print(x['id']) for x in json.load(sys.stdin) if x.get('warehouse_id')=='$WAREHOUSE_ID']")
QSQL="SELECT row_number() OVER (ORDER BY p.published_date DESC) AS n, s.title_pt AS post, s.resumo_html AS resumo_html, p.url AS link FROM $CATALOG.$SCHEMA.post_summaries s JOIN $CATALOG.$SCHEMA.blog_posts p ON p.url = s.url WHERE coalesce(s.weekly_sent, false) = false ORDER BY p.published_date DESC"
QUERY_ID=$(databricks queries-legacy create "${P[@]}" --json \
  "$(python3 -c "import json,sys;print(json.dumps({'name':'Blog Digest - query semanal','data_source_id':'$DS_ID','query':sys.argv[1]}))" "$QSQL")" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
echo "    QUERY_ID=$QUERY_ID"

echo "==> 5/9 Legacy SQL alert (template aplicado depois pelo notebook 00)"
ALERT_ID=$(databricks alerts-legacy create "${P[@]}" --json \
  "$(python3 -c "import json,sys;print(json.dumps({'name':'Databricks Blog Digest - Semanal','query_id':sys.argv[1],'rearm':1,'options':{'column':'n','op':'>','value':'0','empty_result_state':'ok','custom_subject':'Databricks Blog — Resumo da semana','custom_body':'(definido pelo notebook 00)'}}))" "$QUERY_ID")" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
echo "    ALERT_ID=$ALERT_ID"

echo "==> 6/9 Notification Destination por destinatário (e-mails ocultos)"
SUBS="[]"
for e in "${SEED_EMAILS[@]}"; do
  DID=$(databricks notification-destinations create "${P[@]}" --json \
    "{\"display_name\":\"Blog Digest :: $e\",\"config\":{\"email\":{\"addresses\":[\"$e\"]}}}" \
    | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
  SUBS=$(python3 -c "import json,sys;l=json.loads(sys.argv[1]);l.append({'destination_id':sys.argv[2]});print(json.dumps(l))" "$SUBS" "$DID")
  echo "    $e -> $DID"
done

echo "==> 7/9 Job de envio 'blog_send_semanal'"
WJOB=$(databricks jobs create "${P[@]}" --json "$(python3 -c "
import json
print(json.dumps({
  'name':'blog_send_semanal','tags':{'projeto':'databricks_blog_digest'},'max_concurrent_runs':1,
  'tasks':[
    {'task_key':'preparar_email','notebook_task':{'notebook_path':'$USER_PATH/00_preparar_email','source':'WORKSPACE','base_parameters':{'alert_id':'$ALERT_ID','query_id':'$QUERY_ID'}}},
    {'task_key':'tem_conteudo','depends_on':[{'task_key':'preparar_email'}],'condition_task':{'op':'GREATER_THAN','left':'{{tasks.preparar_email.values.pendentes}}','right':'0'}},
    {'task_key':'enviar_lotes','depends_on':[{'task_key':'tem_conteudo','outcome':'true'}],'notebook_task':{'notebook_path':'$USER_PATH/04_enviar_lotes','source':'WORKSPACE','base_parameters':{'alert_id':'$ALERT_ID','warehouse_id':'$WAREHOUSE_ID','sa_filter':'$SA_NAME','batch_size':'10','pause_seconds':'20'}}},
    {'task_key':'marcar_enviados','depends_on':[{'task_key':'enviar_lotes'}],'notebook_task':{'notebook_path':'$USER_PATH/03_weekly_log','source':'WORKSPACE'}}
  ],
  'schedule':{'quartz_cron_expression':'$SEND_CRON','timezone_id':'$TIMEZONE','pause_status':'UNPAUSED'},'queue':{'enabled':True}
}))")" | python3 -c "import json,sys;print(json.load(sys.stdin)['job_id'])")
echo "    blog_send_semanal job_id=$WJOB"

echo "==> 8/9 Job diário 'blog_digest_diario' (ingestão + sync)"
databricks jobs create "${P[@]}" --json "$(python3 -c "
import json
print(json.dumps({
  'name':'blog_digest_diario','tags':{'projeto':'databricks_blog_digest'},'max_concurrent_runs':1,
  'tasks':[
    {'task_key':'ingest_and_summarize','notebook_task':{'notebook_path':'$USER_PATH/01_ingest_and_summarize','source':'WORKSPACE'}},
    {'task_key':'sync_recipients','depends_on':[{'task_key':'ingest_and_summarize'}],'notebook_task':{'notebook_path':'$USER_PATH/02_sync_recipients','source':'WORKSPACE','base_parameters':{'weekly_job_id':'$WJOB','enviar_task_key':'enviar_digest','sa_filter':'$SA_NAME'}}}
  ],
  'schedule':{'quartz_cron_expression':'$DAILY_CRON','timezone_id':'$TIMEZONE','pause_status':'UNPAUSED'},'queue':{'enabled':True}
}))")" | python3 -c "import json,sys;print('    blog_digest_diario job_id=',json.load(sys.stdin)['job_id'])"

echo "==> 9/9 Aplica o template do e-mail (roda o notebook 00)"
databricks jobs submit "${P[@]}" --json "$(python3 -c "
import json
print(json.dumps({'run_name':'aplicar template','tasks':[{'task_key':'t','notebook_task':{'notebook_path':'$USER_PATH/00_preparar_email','source':'WORKSPACE','base_parameters':{'alert_id':'$ALERT_ID','query_id':'$QUERY_ID'}}}]}))")" \
  | python3 -c "import json,sys;print('    template:',json.load(sys.stdin).get('state',{}).get('result_state'))"

echo ""
echo "============================================================"
echo " DEPLOY OK. IDs deste ambiente:"
echo "   QUERY_ID = $QUERY_ID"
echo "   ALERT_ID = $ALERT_ID"
echo "   SEND_JOB = $WJOB  (blog_send_semanal)"
echo " Próximos passos:"
echo "   1) rode 'blog_digest_diario' (popula posts + cria destinos/subscriptions)"
echo "   2) rode 'blog_send_semanal' (envia)"
echo " Gerencie a lista em $CATALOG.$SCHEMA.email_recipients"
echo "============================================================"
