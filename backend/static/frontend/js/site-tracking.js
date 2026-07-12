/**
 * Turtle Cruise — page time + funnel tracking (with offline queue)
 */
(function () {
  'use strict';

  var API_BASE = '/api/v1/audit/events/';
  var BATCH_API = '/api/v1/audit/events/batch/';
  var HEARTBEAT_MS = 30000;
  var QUEUE_KEY = 'tc_audit_queue';

  function getCsrfToken() {
    var match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function getSessionId() {
    var id = sessionStorage.getItem('tc_session_id');
    if (!id) {
      id = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + '-' + Math.random().toString(16).slice(2);
      sessionStorage.setItem('tc_session_id', id);
    }
    document.cookie = 'tc_session_id=' + encodeURIComponent(id) + '; path=/; SameSite=Lax';
    return id;
  }

  function readQueue() {
    try {
      var raw = localStorage.getItem(QUEUE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function writeQueue(items) {
    try {
      localStorage.setItem(QUEUE_KEY, JSON.stringify(items.slice(0, 100)));
    } catch (e) {}
  }

  function enqueue(payload) {
    var queue = readQueue();
    queue.push(payload);
    writeQueue(queue);
  }

  function flushQueue() {
    var queue = readQueue();
    if (!queue.length) return;

    fetch(BATCH_API, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
        'X-TC-Session-Id': getSessionId(),
      },
      body: JSON.stringify({ events: queue }),
      credentials: 'same-origin',
    }).then(function (res) {
      if (res.ok) writeQueue([]);
    }).catch(function () {});
  }

  function sendPayload(payload, useBeacon) {
    var body = JSON.stringify(payload);
    if (useBeacon && navigator.sendBeacon) {
      var blob = new Blob([body], { type: 'application/json' });
      if (navigator.sendBeacon(API_BASE, blob)) return;
    }
    fetch(API_BASE, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
        'X-TC-Session-Id': getSessionId(),
      },
      body: body,
      keepalive: true,
      credentials: 'same-origin',
    }).catch(function () {
      if (payload.event_type && payload.event_type.indexOf('page_') !== 0) {
        enqueue(payload);
      }
    });
  }

  window.tcTrackEvent = function (eventType, data) {
    var payload = Object.assign({
      session_id: getSessionId(),
      event_type: eventType,
    }, data || {});
    sendPayload(payload, false);
  };

  var currentView = {
    viewId: (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()),
    startedAt: Date.now(),
    pausedTotal: 0,
    pausedAt: null,
    heartbeatTimer: null,
    hasExited: false,
    extra: {},
  };

  function activeElapsedMs() {
    var now = Date.now();
    var paused = currentView.pausedTotal;
    if (currentView.pausedAt) {
      paused += now - currentView.pausedAt;
    }
    return Math.max(0, now - currentView.startedAt - paused);
  }

  function scrollDepth() {
    var doc = document.documentElement;
    var scrollTop = window.pageYOffset || doc.scrollTop || 0;
    var viewport = window.innerHeight || doc.clientHeight || 0;
    var height = Math.max(doc.scrollHeight, doc.offsetHeight, doc.clientHeight) - viewport;
    if (height <= 0) return 100;
    return Math.min(100, Math.round((scrollTop / height) * 100));
  }

  window.tcTrackPage = function (action, extra) {
    var payload = Object.assign({
      session_id: getSessionId(),
      event_type: 'page_' + action,
      page_action: 'page_' + action,
      view_id: currentView.viewId,
      path: window.location.pathname,
      page_title: document.title || '',
      locale: document.documentElement.lang || '',
    }, extra || {}, currentView.extra || {});
    sendPayload(payload, action === 'exit');
  };

  function startPageTracking() {
    window.tcTrackPage('enter');

    currentView.heartbeatTimer = window.setInterval(function () {
      if (document.visibilityState !== 'visible') return;
      window.tcTrackPage('heartbeat', {
        duration_ms: activeElapsedMs(),
        scroll_depth_pct: scrollDepth(),
      });
    }, HEARTBEAT_MS);
  }

  function stopPageTracking() {
    if (currentView.hasExited) return;
    currentView.hasExited = true;

    if (currentView.heartbeatTimer) {
      clearInterval(currentView.heartbeatTimer);
      currentView.heartbeatTimer = null;
    }

    window.tcTrackPage('exit', {
      duration_ms: activeElapsedMs(),
      scroll_depth_pct: scrollDepth(),
    });
  }

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') {
      currentView.pausedAt = Date.now();
      window.tcTrackPage('heartbeat', {
        duration_ms: activeElapsedMs(),
        scroll_depth_pct: scrollDepth(),
      });
      return;
    }
    if (currentView.pausedAt) {
      currentView.pausedTotal += Date.now() - currentView.pausedAt;
      currentView.pausedAt = null;
    }
  });

  window.addEventListener('pagehide', stopPageTracking);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      flushQueue();
      startPageTracking();
    });
  } else {
    flushQueue();
    startPageTracking();
  }

  window.tcSessionId = getSessionId();
})();
