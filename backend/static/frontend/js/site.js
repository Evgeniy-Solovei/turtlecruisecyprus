(function ($) {
  'use strict';

  window.blogAjax = {
    url: '/api/v1/blog/load-more/',
    nonce: '',
  };

  $(document).off('click', '#blog-load-more');
  $(document).on('click', '#blog-load-more', function (e) {
    e.preventDefault();

    var $btn = $(this);
    var page = parseInt($btn.data('page'), 10);
    var perPage = parseInt($btn.data('per-page'), 10);
    var maxPages = parseInt($btn.data('max-pages'), 10);
    var nextPage = page + 1;
    var label = $btn.data('label') || 'Load MORE';

    $btn.text('Loading...').prop('disabled', true);

    function csrf() {
      var m = document.cookie.match(/csrftoken=([^;]+)/);
      return m ? decodeURIComponent(m[1]) : '';
    }

    $.ajax({
      url: blogAjax.url,
      type: 'POST',
      headers: { 'X-CSRFToken': csrf() },
      data: {
        page: nextPage,
        per_page: perPage,
        max_pages: maxPages,
      },
      success: function (res) {
        if (res.success) {
          $('#blog-grid').append(res.data.html);
          $btn.data('page', nextPage).prop('disabled', false).text(label);
          if (!res.data.has_more) {
            $('#blog-load-more-wrap').remove();
          }
        } else {
          $btn.prop('disabled', false).text(label);
        }
      },
      error: function () {
        $btn.prop('disabled', false).text(label);
      },
    });
  });

  $(document).ready(function () {
    var $btn = $('#blog-load-more');
    if ($btn.length) {
      $btn.data('label', $btn.text().trim());
    }
  });

  function fixGalleryPage() {
    var $masonry = $('body.gallery .gallery__masonry');
    if (!$masonry.length) {
      return;
    }
    $masonry.removeClass('gallery-load').addClass('gallery__masonry--static is-loaded');
    $masonry.find('.gallery__item').each(function () {
      $(this).show().css({ display: '', opacity: '', transform: '', transition: '', visibility: '' });
    });
    $('body.gallery .flex-load').hide();
  }

  // Run after theme JS that hides gallery items in batches.
  $(document).ready(function () {
    fixGalleryPage();
    setTimeout(fixGalleryPage, 0);
    setTimeout(fixGalleryPage, 400);
  });
  $(window).on('load', fixGalleryPage);
})(jQuery);
