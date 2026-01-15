(function () {
  function createMap(el) {
    if (!el) {
      return;
    }

    var resourceId = el.getAttribute('data-resource-id');
    var siteUrl = (el.getAttribute('data-site-url') || '').replace(/\/$/, '');
    var latField = el.getAttribute('data-lat-field');
    var lonField = el.getAttribute('data-lon-field');
    var labelField = el.getAttribute('data-label-field');
    var limit = parseInt(el.getAttribute('data-limit') || '1000', 10);

    if (!resourceId || !latField || !lonField) {
      el.innerHTML = '<p class="text-warning">Latitude and longitude fields must be configured for this view.</p>';
      return;
    }

    var mapContainer = document.createElement('div');
    mapContainer.className = 'simple-map-view';
    el.appendChild(mapContainer);

    var loading = document.createElement('div');
    loading.className = 'simple-map-loading';
    loading.textContent = 'Loading map data…';
    mapContainer.appendChild(loading);

    if (typeof L === 'undefined') {
      loading.textContent = 'Leaflet failed to load, cannot draw the map.';
      return;
    }

    // Icon paths are handled by Leaflet CSS (images/marker-*.png)
    // Don't override them here to avoid path conflicts

    var map = L.map(mapContainer).setView([0, 0], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '\u00a9 <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    var markers = L.layerGroup();
    markers.addTo(map);

    var bounds = L.latLngBounds();
    var fetched = 0;
    var chunkSize = Math.min(limit, 500);

    function handleRecords(records) {
      records.forEach(function (record) {
        var lat = parseFloat(record[latField]);
        var lon = parseFloat(record[lonField]);
        if (!isFinite(lat) || !isFinite(lon)) {
          return;
        }
        var marker = L.marker([lat, lon]);
        if (labelField && record[labelField]) {
          marker.bindPopup(String(record[labelField]));
        }
        markers.addLayer(marker);
        bounds.extend([lat, lon]);
      });
    }

    function finish() {
      if (loading && loading.parentNode) {
        loading.parentNode.removeChild(loading);
      }
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [20, 20] });
      }
    }

    function loadChunk(offset) {
      var remaining = limit - fetched;
      if (remaining <= 0) {
        finish();
        return;
      }

      var chunkLimit = Math.min(chunkSize, remaining);
      var url = siteUrl + '/api/3/action/datastore_search?resource_id=' + encodeURIComponent(resourceId) + '&limit=' + chunkLimit + '&offset=' + offset;

      fetch(url)
        .then(function (response) {
          if (!response.ok) {
            throw new Error('HTTP ' + response.status);
          }
          return response.json();
        })
        .then(function (payload) {
          if (!payload.success || !payload.result) {
            throw new Error('API returned an error');
          }
          var records = payload.result.records || [];
          handleRecords(records);
          fetched += records.length;

          if (records.length === 0 || fetched >= limit || records.length < chunkLimit) {
            finish();
            return;
          }

          loadChunk(offset + chunkLimit);
        })
        .catch(function (error) {
          if (loading) {
            loading.textContent = 'Could not load map data (' + error.message + ').';
            loading.classList.add('text-error');
          }
        });
    }

    loadChunk(0);
  }

  function initAll() {
    var nodes = document.querySelectorAll('[data-module="simple-map-view"]');
    for (var i = 0; i < nodes.length; i += 1) {
      createMap(nodes[i]);
    }
  }

  if (typeof window.ckan !== 'undefined' && typeof window.ckan.module === 'function') {
    window.ckan.module('simple-map-view', function () {
      return {
        initialize: function () {
          var element = this.el && this.el[0] ? this.el[0] : this.el;
          createMap(element || this);
        }
      };
    });
  } else {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initAll);
    } else {
      initAll();
    }
  }
})();
