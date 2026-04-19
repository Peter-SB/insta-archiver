---
title: "{{ account_name }}/{{ shortcode }}"
url: "{{ url }}"
account: "{{ account_name }}"
date: {{ date }}
folder: "{{ folder }}"
---

# {{ account_name }} / {{ shortcode }}

**URL:** {{ url }}

## Description

{% if description %}
{{ description }}
{% else %}
_No description._
{% endif %}

## Transcript

{% if transcript %}
{{ transcript }}
{% else %}
_No audio to transcribe._
{% endif %}
