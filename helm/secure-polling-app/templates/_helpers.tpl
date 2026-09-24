{{- define "secure-polling-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "secure-polling-app.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end -}}
{{- end -}}
{{- end }}

{{- define "secure-polling-app.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "secure-polling-app.labels" -}}
helm.sh/chart: {{ include "secure-polling-app.chart" . }}
{{ include "secure-polling-app.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "secure-polling-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "secure-polling-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "secure-polling-app.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "secure-polling-app.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
{{- default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end }}

{{- define "secure-polling-app.configName" -}}
{{- printf "%s-config" (include "secure-polling-app.fullname" .) }}
{{- end }}

{{- define "secure-polling-app.secretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{- .Values.secrets.existingSecret }}
{{- else -}}
{{- printf "%s-secrets" (include "secure-polling-app.fullname" .) }}
{{- end -}}
{{- end }}

{{- define "secure-polling-app.dataName" -}}
{{- printf "%s-data" (include "secure-polling-app.fullname" .) }}
{{- end }}

{{- /*
Resolve a secret value with the following precedence:
1. Explicit value in .Values.secrets.<key>
2. Value stored in the existing Secret (persists auto-generated values across upgrades)
3. The generated/default passed in.

Values are emitted base64-encoded, ready for the Secret `data` map.
*/ -}}
{{- define "secure-polling-app.secretValue" -}}
{{- $existing := lookup "v1" "Secret" .ctx.Release.Namespace (include "secure-polling-app.secretName" .ctx) -}}
{{- $val := index .ctx.Values.secrets .key | default "" -}}
{{- if $val -}}
{{- $val | b64enc }}
{{- else if and $existing (hasKey $existing.data .key) -}}
{{- index $existing.data .key }}
{{- else -}}
{{- .default }}
{{- end -}}
{{- end -}}

{{- /* Resolve the volume that backs /data: the PVC when persistence is
enabled, otherwise a persistent-less emptyDir (data is lost on restart). */ -}}
{{- define "secure-polling-app.dataVolume" -}}
{{- if .Values.persistence.enabled -}}
persistentVolumeClaim:
  claimName: {{ include "secure-polling-app.dataName" . }}
{{- else -}}
emptyDir: {}
{{- end -}}
{{- end }}