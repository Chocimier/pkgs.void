#!/usr/bin/env bash
set -e
# https://validator.w3.org/nu/about.html
vnu=${1:-/usr/lib/vnu.jar}
urls=(
	http://127.0.0.1:8080/
	http://127.0.0.1:8080/no-such-page
	http://127.0.0.1:8080/search
	'http://127.0.0.1:8080/pkgs.void/search?term=xbps&find=Find'
	'http://127.0.0.1:8080/pkgs.void/search?term=xbgkoytinjkpeojdgjewluvlww&find=Find'
	http://127.0.0.1:8080/toc
	http://127.0.0.1:8080/of_day
	http://127.0.0.1:8080/newest
	http://127.0.0.1:8080/sets
	http://127.0.0.1:8080/popular
	http://127.0.0.1:8080/longest_names
	http://127.0.0.1:8080/package
	http://127.0.0.1:8080/package/gcc
	http://127.0.0.1:8080/package/base-system/aarch64-glibc
)
exceptions=( -e 'The "navigation" role is unnecessary for element "nav"')

# ./serve.py &
# java -cp "$vnu" nu.validator.servlet.Main 8888 &
for url in ${urls[@]}; do
	echo Checking $url
	wget -q --content-on-error -O - $url | java -cp "$vnu" nu.validator.client.HttpClient 2>&- | grep -v "${exceptions[@]}" | { ! grep . ; }
	wget -q --content-on-error -O - $url | sed 's/<!DOCTYPE html>/<?xml version="1.0"?>/' | python -c 'import sys; from lxml import etree; etree.parse(sys.stdin)'
done
