export function initFarmMapPicker(config = {}) {
  const {
    modalId = 'farmMapModal',
    mapId = 'farmMap',
    openBtnId = 'pickMapBtn',
    closeBtnId = 'closeMapModalBtn',
    cancelBtnId = 'cancelMapPickBtn',
    confirmBtnId = 'confirmMapPickBtn',
    searchInputId = 'farmLocationQuery',
    searchBtnId = 'locateMapBtn',
    pinInputId = 'googlePinLocation',
    pinTextId = 'googlePinLocationText',
    latInputId = 'farmLatitude',
    lngInputId = 'farmLongitude',
    addressInputId = 'farmAddress',
    onPinConfirmed = null
  } = config;

  const modal = document.getElementById(modalId);
  const openBtn = document.getElementById(openBtnId);
  const closeBtn = document.getElementById(closeBtnId);
  const cancelBtn = document.getElementById(cancelBtnId);
  const confirmBtn = document.getElementById(confirmBtnId);
  const searchInput = document.getElementById(searchInputId);
  const searchBtn = document.getElementById(searchBtnId);
  const pinInput = document.getElementById(pinInputId);
  const pinText = document.getElementById(pinTextId);
  const latInput = document.getElementById(latInputId);
  const lngInput = document.getElementById(lngInputId);
  const addressInput = document.getElementById(addressInputId);

  if (!modal || !openBtn || !closeBtn || !cancelBtn || !confirmBtn || !searchInput || !searchBtn || !pinInput || !pinText || !latInput || !lngInput || !addressInput) {
    console.warn('Farm map picker: missing required elements.');
    return {
      hasPin: () => Boolean(pinInput?.value),
      clearPin: () => {}
    };
  }

  if (typeof L === 'undefined') {
    console.warn('Farm map picker: Leaflet is not loaded.');
    return {
      hasPin: () => Boolean(pinInput.value),
      clearPin: () => {}
    };
  }

  let map = null;
  let marker = null;
  let pendingPick = null;

  async function reverseGeocode(lat, lng) {
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`);
      const payload = await res.json();
      return payload?.display_name || '';
    } catch (_) {
      return '';
    }
  }

  async function geocodeAddress(query) {
    try {
      const encoded = encodeURIComponent(query);
      const res = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&q=${encoded}&limit=1`);
      const payload = await res.json();
      if (!Array.isArray(payload) || !payload.length) return null;
      const first = payload[0];
      return {
        lat: Number(first.lat),
        lng: Number(first.lon),
        address: first.display_name || query
      };
    } catch (_) {
      return null;
    }
  }

  function setPendingPick(lat, lng, address = '') {
    pendingPick = { lat, lng, address };

    if (!marker) {
      marker = L.marker([lat, lng]).addTo(map);
    } else {
      marker.setLatLng([lat, lng]);
    }
  }

  function ensureMap() {
    if (map) return;

    map = L.map(mapId).setView([12.8797, 121.7740], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    map.on('click', async (e) => {
      const { lat, lng } = e.latlng;
      setPendingPick(lat, lng, '');
      pendingPick.address = await reverseGeocode(lat, lng);
    });
  }

  function openModal() {
    modal.classList.remove('hidden');
    modal.classList.add('flex');

    ensureMap();

    const savedLat = Number(latInput.value || 0);
    const savedLng = Number(lngInput.value || 0);
    if (savedLat && savedLng) {
      setPendingPick(savedLat, savedLng, addressInput.value || '');
      map.setView([savedLat, savedLng], 16);
    }

    setTimeout(() => map.invalidateSize(), 120);
  }

  function closeModal() {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }

  function applyPin(lat, lng, address = '') {
    const latFixed = Number(lat).toFixed(6);
    const lngFixed = Number(lng).toFixed(6);
    const mapLink = `https://maps.google.com/?q=${latFixed},${lngFixed}`;

    pinInput.value = mapLink;
    latInput.value = String(latFixed);
    lngInput.value = String(lngFixed);
    addressInput.value = address || `${latFixed}, ${lngFixed}`;
    pinText.textContent = addressInput.value ? `📍 ${addressInput.value}` : `📍 ${latFixed}, ${lngFixed}`;

    if (typeof onPinConfirmed === 'function') {
      onPinConfirmed({ lat: latFixed, lng: lngFixed, link: mapLink, address: addressInput.value });
    }
  }

  openBtn.addEventListener('click', openModal);
  closeBtn.addEventListener('click', closeModal);
  cancelBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  confirmBtn.addEventListener('click', () => {
    if (!pendingPick) {
      alert('Please click a location on the map first.');
      return;
    }

    applyPin(pendingPick.lat, pendingPick.lng, pendingPick.address || '');
    closeModal();
  });

  searchBtn.addEventListener('click', async () => {
    const query = searchInput.value.trim();
    if (!query) {
      alert('Please type a farm location first.');
      return;
    }

    searchBtn.disabled = true;
    const originalText = searchBtn.textContent;
    searchBtn.textContent = 'Locating...';

    const result = await geocodeAddress(query);
    if (!result) {
      alert('Location not found. Please use a more specific address or pin directly on the map.');
      searchBtn.disabled = false;
      searchBtn.textContent = originalText;
      return;
    }

    openModal();
    setPendingPick(result.lat, result.lng, result.address || query);
    map.setView([result.lat, result.lng], 16);

    searchBtn.disabled = false;
    searchBtn.textContent = originalText;
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      searchBtn.click();
    }
  });

  return {
    hasPin() {
      return pinInput.value.trim() !== '';
    },
    clearPin() {
      pendingPick = null;
      pinInput.value = '';
      latInput.value = '';
      lngInput.value = '';
      addressInput.value = '';
      pinText.textContent = 'No pin selected yet';
      if (marker && map) {
        map.removeLayer(marker);
        marker = null;
      }
    }
  };
}
