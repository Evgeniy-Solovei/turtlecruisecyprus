/**
 * Cruise Booking Popup — jQuery Logic
 * Turtle Cruise Cyprus by SCUBACAT
 */

;(function($) {
  'use strict';

  // ─── Config ─────────────────────────────────────────────────────────────────

  // Ціни та дані з MotoPress через wp_localize_script
  var PRICES = {
    morning_adult:  (tcBooking.prices && tcBooking.prices.morning_adult) ? parseFloat(tcBooking.prices.morning_adult) : 45,
    morning_child:  (tcBooking.prices && tcBooking.prices.morning_child) ? parseFloat(tcBooking.prices.morning_child) : 25,
    sunset_adult:   (tcBooking.prices && tcBooking.prices.sunset_adult)  ? parseFloat(tcBooking.prices.sunset_adult)  : 35,
  };

  /** Apply day-specific prices from /availability/ (same source as capacity). */
  function applyAvailabilityPrices(cruiseType, data) {
    if (!data || data.adult_price == null) return;
    var adult = parseFloat(data.adult_price);
    if (isNaN(adult)) return;
    if (cruiseType === 'morning') {
      PRICES.morning_adult = adult;
      if (data.child_price != null) {
        var child = parseFloat(data.child_price);
        if (!isNaN(child)) PRICES.morning_child = child;
      }
    } else {
      PRICES.sunset_adult = adult;
    }
  }

  var SERVICES = (tcBooking.services && tcBooking.services.morning) ? tcBooking.services : {
    morning: { title: 'Morning Chill Out Cruise with BBQ', duration_label: '4h 30m' },
    sunset:  { title: 'Sunset Cruise', duration_label: '4h' },
  };

  var DAYS_OFF = (tcBooking.daysOff) ? tcBooking.daysOff : { morning: [], sunset: [] };
  var WORKING_DAYS = (tcBooking.workingDays) ? tcBooking.workingDays : { morning: [0,1,2,3,4,5,6], sunset: [0,1,2,3,4,5,6] };

  var CONTENT = (tcBooking.content) ? tcBooking.content : {};

  var ROUTES = {
    morning: CONTENT.morning_route || 'Ayia Napa Harbour (Limanaki) — Protaras',
    sunset:  CONTENT.sunset_route  || 'Ayia Napa Harbour (Limanaki) — Konnos Bay',
  };

  var TIMES = {
    morning: CONTENT.morning_time || '9:30–14:00',
    sunset:  CONTENT.sunset_time  || '16:00–20:00',
  };

  function getCsrfToken() {
    var match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function apiUrl(path) {
    return tcBooking.apiBaseUrl.replace(/\/$/, '') + path;
  }

  function apiPost(path, body) {
    return $.ajax({
      url: apiUrl(path),
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(body || {}),
      headers: { 'X-CSRFToken': getCsrfToken() },
    });
  }

  function apiGet(path) {
    return $.ajax({ url: apiUrl(path), type: 'GET' });
  }

  function apiErrorMessage(xhr) {
    try {
      var data = JSON.parse(xhr.responseText);
      return data.detail || data.message || 'Request failed.';
    } catch (e) {
      return 'Request failed.';
    }
  }

  var visitorSessionId = sessionStorage.getItem('tc_session_id');
  if (!visitorSessionId) {
    visitorSessionId = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now());
    sessionStorage.setItem('tc_session_id', visitorSessionId);
  }

  function tcTrack(eventType, data) {
    var payload = $.extend({
      step: String(state.currentStep || ''),
      cruise_code: state.cruiseType || '',
      booking_id: state.bookingId || '',
    }, data || {});
    if (typeof window.tcTrackEvent === 'function') {
      window.tcTrackEvent(eventType, payload);
    }
    if (window.dataLayer) {
      window.dataLayer.push($.extend({ event: eventType }, payload));
    }
  }

  // ─── State ──────────────────────────────────────────────────────────────────

  var state = {
    currentStep:  1,
    cruiseType:   null,   // 'morning' | 'sunset'
    date:         null,
    adults:       1,
    children:     0,
    total:        0,
    availableSpots: null, // from /availability/ API (confirmed-only)
    firstName:    '',
    lastName:     '',
    email:        '',
    phone:        '',
    notes:        '',
    bookingId:    null,
    statusPollInterval: null,
  };

  // ─── intl-tel-input instance ────────────────────────────────────────────────
  var itiInstance = null;

  // ─── Cache DOM ──────────────────────────────────────────────────────────────

  var $popup        = $('#tcPopup');
  var $overlay      = $('#tcPopupOverlay');
  var $closeBtn     = $('#tcPopupClose');

  // Steps
  var $step1        = $('#tcStep1');
  var $step2        = $('#tcStep2');
  var $step3        = $('#tcStep3');
  var $stepBlocked  = $('#tcStepBlocked');
  var $stepSuccess  = $('#tcStepSuccess');

  // Step indicators
  var $stepDots     = $('.tc-popup__step');

  // Step 1
  var $dateInput    = $('#tcDate');
  var $adultVal     = $('#tcAdultsVal');
  var $childVal     = $('#tcChildrenVal');
  var $childrenField = $('#tcChildrenField');
  var $adultsPrice  = $('#tcAdultsPrice');
  var $childrenPrice = $('#tcChildrenPrice');
  var $totalAmount  = $('#tcTotalAmount');
  var $termsToggle  = $('#tcTermsToggle');
  var $termsBody    = $('#tcTermsBody');
  var $termsAgree   = $('#tcTermsAgree');
  var $termsBlock   = $('.tc-terms');
  var $summaryPlaceholder = $('#tcSummaryPlaceholder');
  var $summaryFilled      = $('#tcSummaryFilled');

  // Step 2
  var $firstName    = $('#tcFirstName');
  var $lastName     = $('#tcLastName');
  var $email        = $('#tcEmail');
  var $phone        = $('#tcPhone');
  var $notes        = $('#tcNotes');

  // ─── Handle redirect return (Revolut, Bancontact etc.) ─────────────────────

  function tc_handle_payment_return() {
    var urlParams = new URLSearchParams(window.location.search);
    var sessionId = urlParams.get('session_id');
    var bookingId = urlParams.get('booking_id') || localStorage.getItem('tc_pending_booking_id');
    if (!sessionId || !bookingId) return;

    localStorage.removeItem('tc_pending_booking_id');
    apiPost('/payments/stripe/confirm/', {
      booking_id: bookingId,
      checkout_session_id: sessionId,
    }).done(function() {
      tcTrack('payment_completed', { step: '4', completed: true, booking_id: bookingId });
      if (tcBooking.thankYouUrl && window.location.pathname.indexOf('/thank-you') === -1) {
        window.location.href = tcBooking.thankYouUrl;
      }
    }).fail(function(xhr) {
      apiGet('/bookings/' + encodeURIComponent(bookingId) + '/status/')
        .done(function(data) {
          if (data.status === 'confirmed') {
            if (window.history && window.history.replaceState) {
              window.history.replaceState({}, document.title, window.location.pathname);
            }
            return;
          }
          var msg = (tcBooking.i18n.paymentConfirmFailed || '').replace('{booking_id}', bookingId);
          if (!msg) msg = apiErrorMessage(xhr);
          if (window.location.pathname.indexOf('/thank-you') !== -1) {
            var $box = $('#tcThankYouConfirmError');
            if ($box.length) {
              $box.text(msg).prop('hidden', false);
            }
          } else {
            alert(msg);
          }
        })
        .fail(function() {
          var msg = (tcBooking.i18n.paymentConfirmFailed || '').replace('{booking_id}', bookingId);
          alert(msg || apiErrorMessage(xhr));
        });
    }).always(function() {
      if (window.history && window.history.replaceState && window.location.search.indexOf('session_id=') !== -1) {
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    });
  }

  tc_handle_payment_return();

  // ─── Open / Close ───────────────────────────────────────────────────────────

  function openPopup(cruiseType) {
    if (!$('#tcStep1').length) {
      window.location.reload();
      return;
    }

    if (cruiseType) {
      // Конкретний круїз — вибираємо і ховаємо другий
      state.cruiseType = cruiseType;
      $('input[name="cruise_type"][value="' + cruiseType + '"]').prop('checked', true);

      // Сховати інший варіант
      $('.tc-cruise-option').each(function() {
        var val = $(this).find('input[name="cruise_type"]').val();
        if (val !== cruiseType) {
          $(this).hide();
        } else {
          $(this).show();
        }
      });

      updateCruiseUI();
    } else {
      // Загальний букінг — показати обидва неактивними
      $('input[name="cruise_type"]').prop('checked', false);
    $('.tc-cruise-option').show();
      $('.tc-cruise-option').show();
      state.cruiseType = null;
    }

    $popup.addClass('is-open');
    $('body').css('overflow', 'hidden');
    tcTrack('popup_open', { step: '1', cruise_code: cruiseType || '' });
  }

  function closePopup() {
    if ($popup.hasClass('is-open') && state.currentStep < 4 && !state.bookingId) {
      tcTrack('popup_abandoned', { step: String(state.currentStep), abandoned: true });
    } else if ($popup.hasClass('is-open') && state.bookingId && state.currentStep === 3) {
      tcTrack('payment_abandoned', { step: '3', abandoned: true, booking_id: state.bookingId });
    }
    $popup.removeClass('is-open');
    $('body').css('overflow', '');
    stopBookingStatusPoll();
    resetPopup();
  }

  function resetPopup() {
    state.currentStep  = 1;
    state.cruiseType   = null;
    state.date         = null;
    state.adults       = 1;
    state.children     = 0;
    state.total        = 0;
    state.availableSpots = null;
    state.bookingId    = null;
    state.firstName    = '';
    state.lastName     = '';
    state.email        = '';
    state.phone        = '';
    state.notes        = '';

    destroyStripeCheckout();
    localStorage.removeItem('tc_pending_booking_id');
    $stepBlocked.hide();

    $adultVal.text(1);
    $childVal.text(0);
    $dateInput.val('');
    $firstName.val('');
    $lastName.val('');
    $email.val('');
    $phone.val('');
    $notes.val('');
    $('input[name="cruise_type"]').prop('checked', false);
    $termsAgree.prop('checked', false);
    $termsBlock.removeClass('is-open');
    $totalAmount.text('€0');
    $summaryPlaceholder.show();
    $summaryFilled.hide();

    goToStep(1);
  }

  function stopBookingStatusPoll() {
    if (state.statusPollInterval) {
      clearInterval(state.statusPollInterval);
      state.statusPollInterval = null;
    }
  }

  function startBookingStatusPoll() {
    stopBookingStatusPoll();
    if (!state.bookingId) return;

    function checkBookingStatus() {
      if (!state.bookingId || !tcBooking.apiBaseUrl) return;

      $.ajax({
        url:  tcBooking.apiBaseUrl.replace(/\/$/, '') + '/bookings/' + encodeURIComponent(state.bookingId) + '/status/',
        type: 'GET',
        success: function(data) {
          if (!data) return;
          if (data.cancel_reason === 'sold_out') {
            handleSoldOutClosed();
            return;
          }
          if (data.status === 'expired' || data.cancel_reason === 'hold_expired') {
            handleSessionClosed();
          }
        }
      });
    }

    checkBookingStatus();
    state.statusPollInterval = setInterval(checkBookingStatus, 5000);
  }

  function destroyStripeCheckout() {
    if (stripeCheckout) {
      try { stripeCheckout.destroy(); } catch (e) {}
      stripeCheckout = null;
    }
    $('#tc-payment-element').empty();
    $('#tc-payment-errors').text('');
    $('#tc-stripe-placeholder').show();
  }

  function showBlockedStep(icon, title, message) {
    stopBookingStatusPoll();
    destroyStripeCheckout();

    $('#tcBlockedIcon').text(icon || '🚫');
    $('#tcBlockedTitle').text(title || '');
    $('#tcBlockedMsg').text(message || '');

    $step1.hide();
    $step2.hide();
    $step3.hide();
    $stepSuccess.hide();
    $stepBlocked.show();
    $stepDots.removeClass('active done');
    state.currentStep = 0;
  }

  function handleSoldOutClosed() {
    var soldOutMsg = tcBooking.i18n.fullyBookedPaymentMsg || tcBooking.i18n.fullyBooked;
    showBlockedStep('🚫', tcBooking.i18n.fullyBooked, soldOutMsg);
  }

  function handleSessionClosed() {
    showBlockedStep('⏱', tcBooking.i18n.sessionExpired, tcBooking.i18n.sessionExpiredMsg);
  }

  // ─── Steps Navigation ───────────────────────────────────────────────────────

  function goToStep(n) {
    state.currentStep = n;
    tcTrack('step_view', { step: String(n) });

    $step1.hide();
    $step2.hide();
    $step3.hide();
    $stepBlocked.hide();
    $stepSuccess.hide();

    $stepDots.removeClass('active done');

    switch (n) {
      case 1:
        $step1.show();
        $stepDots.filter('[data-step="1"]').addClass('active');
        break;
      case 2:
        $step2.show();
        fillStep2Summary();
        // Ініціалізувати intl-tel-input
        if ( ! itiInstance && window.intlTelInput && document.getElementById('tcPhone') ) {
          itiInstance = intlTelInput( document.getElementById('tcPhone'), {
            utilsScript: 'https://cdn.jsdelivr.net/npm/intl-tel-input@19.5.6/build/js/utils.js',
            initialCountry: 'cy',
            preferredCountries: ['cy', 'gb', 'de', 'ru', 'ua', 'il', 'us'],
            showSelectedDialCode: true,
            nationalMode: false,
            autoPlaceholder: 'aggressive',
            placeholderNumberType: 'MOBILE',
            dropdownContainer: document.body,
          });
        }
        $stepDots.filter('[data-step="1"]').addClass('done');
        $stepDots.filter('[data-step="2"]').addClass('active');
        break;
      case 3:
        $step3.show();
        fillStep3Summary();
        initStripe();
        startBookingStatusPoll();
        $stepDots.filter('[data-step="1"]').addClass('done');
        $stepDots.filter('[data-step="2"]').addClass('done');
        $stepDots.filter('[data-step="3"]').addClass('active');
        break;
      case 4:
        $stepSuccess.show();
        break;
    }
  }

  // ─── Cruise UI Update ───────────────────────────────────────────────────────

  function updateCruiseUI() {
    var type = state.cruiseType;

    if (type === 'morning') {
      $childrenField.removeClass('is-hidden');
      $adultsPrice.text('€' + PRICES.morning_adult + ' ' + tcBooking.i18n.perPerson);
      $childrenPrice.text('€' + PRICES.morning_child + ' ' + tcBooking.i18n.perPerson);
    } else if (type === 'sunset') {
      $childrenField.addClass('is-hidden');
      $childVal.text(0);
      state.children = 0;
      $adultsPrice.text('€' + PRICES.sunset_adult + ' ' + tcBooking.i18n.perPerson);
    }

    updateTotal();
    updateSummary();
  }

  // ─── Total Calculation ──────────────────────────────────────────────────────

  function updateTotal() {
    var adults   = parseInt($adultVal.text(), 10) || 1;
    var children = parseInt($childVal.text(), 10) || 0;
    var type     = state.cruiseType;
    var total    = 0;

    if (type === 'morning') {
      total = adults * PRICES.morning_adult + children * PRICES.morning_child;
    } else if (type === 'sunset') {
      total = adults * PRICES.sunset_adult;
    }

    state.adults   = adults;
    state.children = children;
    state.total    = total;

    $totalAmount.text('€' + total);
  }

  // ─── Summary (Step 1) ───────────────────────────────────────────────────────

  function updateSummary() {
    var type = state.cruiseType;
    var date = $dateInput.val();

    if (!type || !date) {
      $summaryPlaceholder.show();
      $summaryFilled.hide();
      return;
    }

    $summaryPlaceholder.hide();
    $summaryFilled.show();

    var isMorning = type === 'morning';
    var title     = SERVICES[type].title;
    var time      = isMorning ? TIMES.morning : TIMES.sunset;
    var duration  = SERVICES[type].duration_label + ' duration';
    var dateFormatted = formatDate(date);

    $('#tcSummaryTitle').text(title);
    $('#tcSummaryMeta').text(dateFormatted + ', ' + time + ' (' + duration + ')');
    $('#tcSummaryRoute').text(tcBooking.i18n.route + ' ' + ROUTES[type]);

    // Опис з MotoPress
    var desc = SERVICES[type].description || '';
    var $descEl = $('#tcSummaryDesc');
    if ( $descEl.length === 0 ) {
      $('#tcSummaryPrices').before('<div class="tc-summary__desc" id="tcSummaryDesc"></div>');
    }
    $('#tcSummaryDesc').text(desc);

    var morningAdult = PRICES.morning_adult || 45;
    var morningChild  = PRICES.morning_child  || 25;
    var sunsetAdult   = PRICES.sunset_adult   || 35;
    var contactPhone = CONTENT.phone || '+357 97 719 450';
     var pricesHtml = isMorning
    ? '<div>Adults (10+ y.o.): €' + morningAdult + ' ' + tcBooking.i18n.includingBbq + '</div><div>Children (2–10 y.o.): €' + morningChild + ' ' + tcBooking.i18n.includingBbq + '</div><div style="font-size:0.73rem;margin-top:0.25rem">Infants (0–2 y.o.) — free. Reservations are only available at the offline ticket office or by calling: ' + contactPhone + '</div>'
    : '<div>Adults / Children: €' + sunsetAdult + ' (age 10+)</div>';

    $('#tcSummaryPrices').html(pricesHtml);
  }

  // ─── Summary (Step 2) ───────────────────────────────────────────────────────

  function fillStep2Summary() {
    var isMorning = state.cruiseType === 'morning';
    var title     = SERVICES[state.cruiseType].title;
    var time      = isMorning ? TIMES.morning : TIMES.sunset;

    $('#tcStep2SummaryTitle').text(title);
    $('#tcStep2SummaryMeta').text(formatDate(state.date) + ', ' + time);
    $('#tcStep2SummaryRoute').text(tcBooking.i18n.route + ' ' + ROUTES[state.cruiseType]);
    $('#tcStep2Adults').text(
      tcBooking.i18n.adults + ' ' + state.adults + ' (€' + (isMorning ? PRICES.morning_adult : PRICES.sunset_adult) + ')'
    );

    if (isMorning && state.children > 0) {
      $('#tcStep2ChildrenLine').show();
      $('#tcStep2Children').text(tcBooking.i18n.children + ' ' + state.children + ' (€' + PRICES.morning_child + ')');
    } else {
      $('#tcStep2ChildrenLine').hide();
    }

    $('#tcStep2Total').text('€' + state.total);
  }

  // ─── Summary (Step 3) ───────────────────────────────────────────────────────

  function fillStep3Summary() {
    var isMorning = state.cruiseType === 'morning';
    var title     = SERVICES[state.cruiseType].title;
    var time      = isMorning ? TIMES.morning : TIMES.sunset;

    $('#tcStep3SummaryTitle').text(title);
    $('#tcStep3SummaryMeta').text(formatDate(state.date) + ', ' + time);
    $('#tcStep3SummaryRoute').text(tcBooking.i18n.route + ' ' + ROUTES[state.cruiseType]);
    $('#tcStep3Person').text(state.firstName + ' ' + state.lastName);
    $('#tcStep3Email').text(state.email);

    if (state.notes) {
      $('#tcStep3Notes').text(state.notes);
    }

    $('#tcStep3Adults').text(tcBooking.i18n.adults + ' ' + state.adults);

    if (isMorning && state.children > 0) {
      $('#tcStep3ChildrenLine').show().text(tcBooking.i18n.children + ' ' + state.children);
    } else {
      $('#tcStep3ChildrenLine').hide();
    }

    $('#tcStep3Total').text('€' + state.total);
  }

  // ─── Validation ─────────────────────────────────────────────────────────────

  function validateStep1() {
    var date = $dateInput.val();
    var type = $('input[name="cruise_type"]:checked').val() || state.cruiseType;

    if (!date) {
      alert(tcBooking.i18n.selectDate);
      $dateInput.focus();
      return false;
    }

    if (!type) {
      if ($('input[name="cruise_type"]').length === 0) {
        alert('Cruises are not configured yet. Import site data or add cruises in admin.');
      } else {
        alert(tcBooking.i18n.selectCruise);
      }
      return false;
    }

    if ($('input[name="cruise_type"][value="' + type + '"]').length) {
      $('input[name="cruise_type"][value="' + type + '"]').prop('checked', true);
    }

    if (!$termsAgree.is(':checked')) {
      alert(tcBooking.i18n.agreeTerms);
      return false;
    }

    var adults = readAdults();
    var children = readChildren();
    if (state.availableSpots !== null && adults + children > state.availableSpots) {
      var msg = (tcBooking.i18n.tooManySeats || 'You can only book up to {n} seats for this date.')
        .replace('{n}', String(state.availableSpots));
      alert(msg);
      return false;
    }

    state.date       = date;
    state.cruiseType = type;

    return true;
  }

  function validateStep2() {
    var first = $.trim($firstName.val());
    var last  = $.trim($lastName.val());
    var email = $.trim($email.val());
    var phoneNum = $.trim($phone.val());
    var phone    = itiInstance ? itiInstance.getNumber() : phoneNum;

    if (!first)    { alert(tcBooking.i18n.enterFirstName); $firstName.focus(); return false; }
    if (!last)     { alert(tcBooking.i18n.enterLastName); $lastName.focus(); return false; }
    if (!email || !isValidEmail(email)) { alert(tcBooking.i18n.enterEmail); $email.focus(); return false; }
    if (!phoneNum) { alert(tcBooking.i18n.enterPhone); $phone.focus(); return false; }
    if (itiInstance && !itiInstance.isValidNumber()) {
      alert(tcBooking.i18n.invalidPhone); $phone.focus(); return false;
    }

    state.firstName = first;
    state.lastName  = last;
    state.email     = email;
    state.phone     = phone;
    state.notes     = $.trim($notes.val());

    return true;
  }

  // ─── AJAX: Create Booking ───────────────────────────────────────────────────

  function createBooking(callback) {
    apiPost('/bookings/hold/', {
      cruise_code: state.cruiseType,
      cruise_date: state.date,
      adults_count: state.adults,
      children_count: state.children,
      first_name: state.firstName,
      last_name: state.lastName,
      email: state.email,
      phone: state.phone,
      customer_notes: state.notes,
      session_id: visitorSessionId,
    }).done(function(res) {
      state.bookingId = res.public_id;
      state.total = parseFloat(res.total_amount);
      tcTrack('booking_created', { step: '3', booking_id: res.public_id, payload: { total: res.total_amount } });
      callback(null, res);
    }).fail(function(xhr) {
      callback(apiErrorMessage(xhr));
    });
  }

  // ─── AJAX: Confirm Payment ──────────────────────────────────────────────────

  function confirmPayment(paymentId, callback) {
    var payload = { booking_id: state.bookingId };
    if (paymentId && paymentId.indexOf('cs_') === 0) {
      payload.checkout_session_id = paymentId;
    } else {
      payload.payment_intent_id = paymentId;
    }
    apiPost('/payments/stripe/confirm/', payload)
      .done(function() { callback(null); })
      .fail(function(xhr) { callback(apiErrorMessage(xhr)); });
  }

  // ─── Passenger counters (adults + children share one availability pool) ─────

  function readAdults() {
    return parseInt($adultVal.text(), 10) || 1;
  }

  function readChildren() {
    return parseInt($childVal.text(), 10) || 0;
  }

  function seatCap() {
    if (state.availableSpots !== null && state.availableSpots >= 0) {
      return state.availableSpots;
    }
    return 30;
  }

  function maxAdultsAllowed() {
    return Math.max(seatCap() - readChildren(), 1);
  }

  function maxChildrenAllowed() {
    return Math.max(seatCap() - readAdults(), 0);
  }

  function clampPassengerCounts() {
    var adults = readAdults();
    var children = readChildren();
    var cap = seatCap();
    if (adults + children <= cap) {
      return;
    }
    if (adults > cap) {
      adults = Math.max(cap, 1);
      children = 0;
    } else {
      children = Math.max(cap - adults, 0);
    }
    $adultVal.text(adults);
    $childVal.text(children);
    updateTotal();
  }

  // ─── Counter Buttons ────────────────────────────────────────────────────────

  $(document).on('click', '.tc-counter__btn--plus', function() {
    var targetId = $(this).data('target');
    var $val = $('#' + targetId);
    var current = parseInt($val.text(), 10) || 0;
    var max = (targetId === 'tcAdultsVal') ? maxAdultsAllowed() : maxChildrenAllowed();
    if (current < max) {
      $val.text(current + 1);
      updateTotal();
      updateSummary();
    }
  });

  $(document).on('click', '.tc-counter__btn--minus', function() {
    var targetId = $(this).data('target');
    var $val = $('#' + targetId);
    var current = parseInt($val.text(), 10) || 0;
    var min = (targetId === 'tcAdultsVal') ? 1 : 0;
    if (current > min) {
      $val.text(current - 1);
      updateTotal();
      updateSummary();
    }
  });

  // ─── Cruise Radio Change ────────────────────────────────────────────────────

  $(document).on('change', 'input[name="cruise_type"]', function() {
    state.cruiseType = $(this).val();
    updateCruiseUI();
    // Перевірити доступність якщо дата вже вибрана
    if ( state.date ) {
      checkDateAvailability( state.date, state.cruiseType );
    }
  });

  // ─── Date Change ────────────────────────────────────────────────────────────

  $dateInput.on('change', function() {
    var date = $(this).val();
    state.date = date;
    tcTrack('date_selected', { step: '1', payload: { date: date } });
    if ( state.cruiseType && date ) {
      checkDateAvailability( date, state.cruiseType );
    }
    updateSummary();
  });

  // ─── Check Date Availability ─────────────────────────────────────────────────

  function checkDateAvailability( date, cruiseType ) {
    var daysOff   = DAYS_OFF[ cruiseType ] || [];
    var workDays  = WORKING_DAYS[ cruiseType ] || [0,1,2,3,4,5,6];
    var dayOfWeek = new Date( date + 'T12:00:00' ).getDay();
    var $next     = $('#tcStep1Next');
    var $dateWrap = $dateInput.closest('.tc-field');

    $dateWrap.find('.tc-date-message').remove();

    if ( daysOff.indexOf( date ) !== -1 ) {
      showDateMessage( $dateWrap, tcBooking.i18n.dayOff, 'error' );
      $next.prop('disabled', true);
      return;
    }

    if ( workDays.indexOf( dayOfWeek ) === -1 ) {
      showDateMessage( $dateWrap, tcBooking.i18n.noCruises, 'error' );
      $next.prop('disabled', true);
      return;
    }

    apiGet('/cruises/' + encodeURIComponent(cruiseType) + '/availability/?date=' + encodeURIComponent(date))
      .done(function(data) {
        $dateWrap.find('.tc-date-message').remove();
        state.availableSpots = data.available;
        applyAvailabilityPrices(cruiseType, data);

        if (!data.bookable || data.available <= 0) {
          showDateMessage($dateWrap, tcBooking.i18n.fullyBooked, 'error');
          $next.prop('disabled', true);
        } else if (data.available <= 5) {
          showDateMessage($dateWrap, 'Only ' + data.available + ' ' + tcBooking.i18n.spotsLeft, 'warning');
          $next.prop('disabled', false);
        } else {
          showDateMessage($dateWrap, data.available + ' ' + tcBooking.i18n.spotsAvailable, 'success');
          $next.prop('disabled', false);
        }
        clampPassengerCounts();
        updateCruiseUI();
      })
      .fail(function() {
        $next.prop('disabled', false);
      });
  }

  function showDateMessage( $wrap, text, type ) {
    var colors = { error: '#e53935', warning: '#f0a500', success: '#2e7d32' };
    $wrap.append( '<div class="tc-date-message" style="font-size:0.78rem;margin-top:0.375rem;color:' + colors[type] + '">' + text + '</div>' );
  }

  // ─── Terms Accordion ────────────────────────────────────────────────────────

  $termsToggle.on('click', function() {
    $termsBlock.toggleClass('is-open');
  });

  // ─── Step 1 → 2 ────────────────────────────────────────────────────────────

  $('#tcStep1Next').on('click', function() {
    if (!validateStep1()) return;
    goToStep(2);
  });

  // ─── Step 2 → 1 ────────────────────────────────────────────────────────────

  $('#tcStep2Back').on('click', function() {
    goToStep(1);
  });

  // ─── Step 2 → 3 ────────────────────────────────────────────────────────────

  $('#tcStep2Next').on('click', function() {
    if (!validateStep2()) return;

    var $btn = $(this);
    $btn.prop('disabled', true).text('Processing...');

    createBooking(function(err, data) {
      $btn.prop('disabled', false).html('Checkout <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M4 9h10M10 5l4 4-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>');

      if (err) {
        alert(err);
        return;
      }

      goToStep(3);
    });
  });

  // ─── Step 3 → 2 ────────────────────────────────────────────────────────────

  $('#tcStep3Back').on('click', function() {
    goToStep(2);
  });

  // ─── Stripe Elements ────────────────────────────────────────────────────────

  var stripe         = null;
  var stripeCheckout = null;

  function initStripe() {
    if (stripeCheckout) return;
    if (!window.Stripe) {
      console.error('Stripe.js not loaded');
      return;
    }

    stripe = Stripe(tcBooking.stripeKey);

    apiPost('/payments/stripe/payment-intent/', {
      booking_id: state.bookingId,
    }).done(function(res) {
      var clientSecret = res.client_secret;
      if (state.bookingId) {
        localStorage.setItem('tc_pending_booking_id', state.bookingId);
      }
      stripe.initEmbeddedCheckout({ clientSecret: clientSecret })
        .then(function(checkout) {
          stripeCheckout = checkout;
          tcTrack('payment_started', { step: '3', booking_id: state.bookingId });
          checkout.mount('#tc-payment-element');
          $('#tc-express-checkout-wrap').hide();
          $('#tcPlaceOrder').hide();
          $('#tc-stripe-placeholder').hide();
        })
        .catch(function(err) {
          $('#tc-payment-errors').text(err.message || 'Could not load payment form.');
        });
    }).fail(function(xhr) {
      $('#tc-payment-errors').text(apiErrorMessage(xhr));
    });
  }

  // Place Order hidden — payment is inside Stripe Embedded Checkout

  // ─── Close ──────────────────────────────────────────────────────────────────

  $closeBtn.on('click', closePopup);
  $overlay.on('click', closePopup);
  $('#tcSuccessClose').on('click', closePopup);
  $('#tcBlockedRestart').on('click', closePopup);

  $(document).on('keydown', function(e) {
    if (e.key === 'Escape' && $popup.hasClass('is-open')) {
      closePopup();
    }
  });

  if (tcBooking.minDate) {
    $dateInput.attr('min', tcBooking.minDate);
  }

  // ─── Open Triggers ──────────────────────────────────────────────────────────

  // Кнопки на сторінці — будь-який елемент з data-cruise-open
  $(document).on('click', '[data-cruise-open]', function() {
    var type = $(this).data('cruise-open') || null;
    openPopup(type);
  });

  // Глобальна функція для виклику з будь-якого місця
  window.tcOpenBooking = openPopup;

  // ─── Helpers ────────────────────────────────────────────────────────────────

  function formatDate(dateStr) {
    if (!dateStr) return '';
    var d = new Date(dateStr + 'T12:00:00');
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

})(jQuery);