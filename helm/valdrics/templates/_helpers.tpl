{{/*
Expand the name of the chart.
*/}}
{{- define "valdrics.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "valdrics.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "valdrics.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "valdrics.labels" -}}
helm.sh/chart: {{ include "valdrics.chart" . }}
{{ include "valdrics.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "valdrics.selectorLabels" -}}
app.kubernetes.io/name: {{ include "valdrics.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "valdrics.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "valdrics.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Resolve the Kubernetes Secret name that backs runtime configuration.
*/}}
{{- define "valdrics.runtimeSecretName" -}}
{{- if .Values.externalSecrets.enabled -}}
{{- .Values.externalSecrets.target.name -}}
{{- else -}}
{{- .Values.existingSecrets.name -}}
{{- end -}}
{{- end }}

{{/*
Resolve the public API hostname for strict-environment base URL settings.
*/}}
{{- define "valdrics.apiHost" -}}
{{- $host := "" -}}
{{- if and .Values.ingress.enabled (gt (len .Values.ingress.hosts) 0) -}}
{{- $host = (index .Values.ingress.hosts 0).host | default "" -}}
{{- end -}}
{{- if $host -}}
{{- $host -}}
{{- else -}}
{{- printf "%s.%s" .Values.global.subdomain .Values.global.baseDomain -}}
{{- end -}}
{{- end }}

{{/*
Resolve the frontend hostname for strict-environment base URL settings.
*/}}
{{- define "valdrics.frontendHost" -}}
{{- printf "%s.%s" .Values.global.frontendSubdomain .Values.global.baseDomain -}}
{{- end }}

{{- define "valdrics.apiUrl" -}}
{{- printf "https://%s" (include "valdrics.apiHost" .) -}}
{{- end }}

{{- define "valdrics.frontendUrl" -}}
{{- printf "https://%s" (include "valdrics.frontendHost" .) -}}
{{- end }}
