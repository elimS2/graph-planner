/* PlainPaste helper: reusable plain-text paste wiring for contenteditable elements */
(function (global) {
  'use strict';

  function sanitizePlainText(input, options) {
    try {
      var text = String(input || '');
      var allowNewlines = !!(options && options.allowNewlines);
      if (allowNewlines) {
        text = text.replace(/\r\n?/g, '\n');
      } else {
        text = text.replace(/[\r\n]+/g, ' ');
      }
      text = text.replace(/\s{2,}/g, ' ').trim();
      return text;
    } catch (_) {
      return '';
    }
  }

  function insertTextAtCaret(containerEl, text) {
    try {
      var selection = global.getSelection ? global.getSelection() : null;
      if (!selection) {
        containerEl.textContent = String(containerEl.textContent || '') + text;
        return;
      }
      if (selection.rangeCount === 0 || !containerEl.contains(selection.anchorNode)) {
        // place caret at end of container
        containerEl.focus();
        var endRange = document.createRange();
        endRange.selectNodeContents(containerEl);
        endRange.collapse(false);
        selection.removeAllRanges();
        selection.addRange(endRange);
      }
      var range = selection.getRangeAt(0);
      range.deleteContents();
      var textNode = document.createTextNode(text);
      range.insertNode(textNode);
      // move caret after inserted text
      var after = document.createRange();
      after.setStartAfter(textNode);
      after.collapse(true);
      selection.removeAllRanges();
      selection.addRange(after);
    } catch (_) {}
  }

  function wirePlainTextPaste(el, options) {
    if (!el) return function noop() {};

    var onPaste = function (e) {
      try {
        var cd = e.clipboardData;
        if (!cd) return;
        var txt = cd.getData('text/plain');
        if (typeof txt === 'string') {
          e.preventDefault();
          insertTextAtCaret(el, sanitizePlainText(txt, options));
        }
      } catch (_) {}
    };

    var preventDrop = !!(options && options.preventDrop);
    var onDragOver = function (e) {
      if (!preventDrop) return;
      try { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'none'; } catch (_) {}
    };
    var onDrop = function (e) {
      if (!preventDrop) return;
      try { e.preventDefault(); e.stopPropagation(); el.focus(); } catch (_) {}
    };

    el.addEventListener('paste', onPaste);
    if (preventDrop) {
      el.addEventListener('dragover', onDragOver);
      el.addEventListener('drop', onDrop);
    }

    return function unWire() {
      try { el.removeEventListener('paste', onPaste); } catch (_) {}
      if (preventDrop) {
        try { el.removeEventListener('dragover', onDragOver); } catch (_) {}
        try { el.removeEventListener('drop', onDrop); } catch (_) {}
      }
    };
  }

  global.PlainPaste = {
    sanitizePlainText: sanitizePlainText,
    insertTextAtCaret: insertTextAtCaret,
    wirePlainTextPaste: wirePlainTextPaste
  };
})(window);


