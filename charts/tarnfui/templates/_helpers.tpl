{{/*
Define helper functions for Tarnfui
*/}}

{{/*
Generate a comma-separated list of resource types based on configuration
*/}}
{{- define "tarnfui.resourceTypes" -}}
{{- $types := list -}}
{{- if .Values.tarnfui.resourceTypes.deployments -}}
{{- $types = append $types "deployments" -}}
{{- end -}}
{{- if .Values.tarnfui.resourceTypes.statefulsets -}}
{{- $types = append $types "statefulsets" -}}
{{- end -}}
{{- if .Values.tarnfui.resourceTypes.cronjobs -}}
{{- $types = append $types "cronjobs" -}}
{{- end -}}
{{- join "," $types -}}
{{- end -}}