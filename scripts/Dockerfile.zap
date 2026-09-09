FROM zaproxy/zap-stable
# Add-ons congelados para o experimento
RUN zap.sh -cmd -addonupdate \
    -addoninstall ascanrulesBeta \
    -addoninstall ascanrulesAlpha \
    -addoninstall ajaxSpider \
    -addoninstall accessControl \
    -addoninstall jwt \
    -addoninstall reports \
    -addoninstall automation
