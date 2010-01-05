from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('',
    #(r'^accounts/', include('registration.urls')),
    (r'', include('richtemplates.examples.urls')),

)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % settings.MEDIA_URL.strip('/'), 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),
)

