(function () {
  'use strict';

  var STORAGE_KEY = 'tc_cookie_consent';
  var gtmId = window.tcGtmId || (window.tcBooking && window.tcBooking.gtmContainerId) || '';

  function loadGtm() {
    if (!gtmId || window.__tcGtmLoaded) return;
    window.__tcGtmLoaded = true;
    (function (w, d, s, l, i) {
      w[l] = w[l] || [];
      w[l].push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
      var f = d.getElementsByTagName(s)[0];
      var j = d.createElement(s);
      var dl = l !== 'dataLayer' ? '&l=' + l : '';
      j.async = true;
      j.src = 'https://www.googletagmanager.com/gtm.js?id=' + i + dl;
      f.parentNode.insertBefore(j, f);
    })(window, document, 'script', 'dataLayer', gtmId);
  }

  function setConsent(granted) {
    if (typeof gtag === 'function') {
      gtag('consent', 'update', {
        analytics_storage: granted ? 'granted' : 'denied',
        ad_storage: granted ? 'granted' : 'denied',
        ad_user_data: granted ? 'granted' : 'denied',
        ad_personalization: granted ? 'granted' : 'denied',
      });
    }
    if (granted) loadGtm();
  }

  function hideBanner() {
    var el = document.getElementById('tcConsent');
    if (el) el.hidden = true;
  }

  function showBanner() {
    var el = document.getElementById('tcConsent');
    if (el) el.hidden = false;
  }

  function saveChoice(value) {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch (e) {}
  }

  function readChoice() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    var existing = readChoice();
    if (existing === 'accepted') {
      setConsent(true);
      hideBanner();
      return;
    }
    if (existing === 'rejected') {
      setConsent(false);
      hideBanner();
      return;
    }
    showBanner();
    document.getElementById('tcConsentAccept').addEventListener('click', function () {
      saveChoice('accepted');
      setConsent(true);
      hideBanner();
    });
    document.getElementById('tcConsentReject').addEventListener('click', function () {
      saveChoice('rejected');
      setConsent(false);
      hideBanner();
    });
  });
})();
