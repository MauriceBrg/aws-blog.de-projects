#! /bin/bash
CURRENT_DATE=$(date)

cat index_template.html | sed -e "s/BUILDTIME/${CURRENT_DATE}/g" > index.html