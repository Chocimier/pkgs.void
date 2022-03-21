#!/bin/sh
: "${void_packages:=https://github.com/void-linux/void-packages}"
: "${XBPS_DISTDIR:=/var/www/void-packages}"

if [ "$1" != -T ]; then
	if ! [ -d "$XBPS_DISTDIR" ]; then
		git clone --depth 1 "$void_packages" "$XBPS_DISTDIR" || exit $?
	fi
fi
env PATH=$PATH:/var/www/xtools XBPS_DISTDIR=$XBPS_DISTDIR /var/www/pkgs.void/update.sh "$@"
