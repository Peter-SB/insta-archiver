---
title: "{{ channel }}/{{ video_id }}"
url: "{{ url }}"
channel: "{{ channel }}"
title_text: "{{ title }}"
upload_date: "{{ upload_date }}"
view_count: {{ view_count if view_count is not none else "~" }}
like_count: {{ like_count if like_count is not none else "~" }}
channel_followers: {{ channel_followers if channel_followers is not none else "~" }}
date: {{ date }}
folder: "{{ folder }}"
---

# {{ title }}

**Channel:** {{ channel }}
**URL:** {{ url }}
**Uploaded:** {{ upload_date }}
{% if view_count is not none %}**Views:** {{ "{:,}".format(view_count) }}{% endif %}
{% if like_count is not none %}**Likes:** {{ "{:,}".format(like_count) }}{% endif %}
{% if channel_followers is not none %}**Subscribers:** {{ "{:,}".format(channel_followers) }}{% endif %}

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
