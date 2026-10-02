{{- define "testlens.labels" -}}
app.kubernetes.io/part-of: testlens
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{- define "testlens.image" -}}
{{- $root := index . 0 -}}
{{- $repo := index . 1 -}}
{{- $tag := default $root.Chart.AppVersion $root.Values.image.tag -}}
{{- if $root.Values.image.registry -}}
{{ $root.Values.image.registry }}/{{ $repo }}:{{ $tag }}
{{- else -}}
{{ $repo }}:{{ $tag }}
{{- end -}}
{{- end }}

{{- define "testlens.apiEnv" -}}
{{- range $name, $value := .Values.api.env }}
- name: {{ $name }}
  value: {{ $value | quote }}
{{- end }}
{{- range list "DATABASE_URL" "REDIS_URL" "ANTHROPIC_API_KEY" }}
- name: {{ . }}
  valueFrom:
    secretKeyRef:
      name: {{ $.Values.existingSecret }}
      key: {{ . }}
{{- end }}
{{- end }}
