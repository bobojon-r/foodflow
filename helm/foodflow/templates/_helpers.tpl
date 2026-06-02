{{/*
Database URL for a given service name (auth, restaurant, order)
*/}}
{{- define "foodflow.dbUrl" -}}
{{- $svc := . -}}
postgresql+asyncpg://{{ "{{" }} .Values.postgres.user {{ "}}" }}:{{ "{{" }} .Values.postgres.password {{ "}}" }}@db-{{ $svc }}:5432/{{ $svc }}_db
{{- end }}
