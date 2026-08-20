(function () {
  if (window.__astrovedWidgetLoaded) return;
  window.__astrovedWidgetLoaded = true;

  var API = window.location.origin;
  var SITE = 'https://www.astroved.com';
  var CRM_KW = ['payment', 'pay', 'billing', 'bill', 'invoice', 'refund', 'subscription',
    'plan', 'price', 'pricing', 'cost', 'charge', 'cancel', 'complaint', 'support',
    'agent', 'human', 'team', 'speak', 'talk', 'call me', 'account', 'orders', 'tracking'];

  /* ── AstroVed Logo Base64 ── */
  var LOGO_SRC = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAWgAAAFoCAYAAAB65WHVAAABhmlDQ1BJQ0MgcHJvZmlsZQAAKJGjkLFKA0EQht9ECUGJiIWFhY+QQ7GJIipiJRYWgoVGMRpMLsc5uZzHkbsgNo+ghbWNnYWNb2BhYWMvBMEXECsLsZFsdhMPE8k6sDvf/szssDMDpBuWZflDAMuo3EyckBbZJek/IYKnRxAiJNOyvDSbzTL0fR8rBO89U6u993trDnJpZQqEo4T8YFVuiUfieb2qBuWOuGVV5o64I07rckLcVXpU8IPinYrHittKZxIzhDqJha2fbBe3xW1xT3xSXZHLBxxHpf86cFBrmbZ3WuSoqSqphBRTUKihRIEKGmJqqGmhJkOdS6CoJCOZS54lzyp7lj0Lni3PjmfTs7PJIiISRRRRxhlFFFFEEUMkIkIW2f8P2L0DAO66Ng8=";

  /* ── Inject Google Fonts ── */
  var fontLink = document.createElement('link');
  fontLink.rel = 'stylesheet';
  fontLink.href = 'https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap';
  document.head.appendChild(fontLink);

  /* ── Inject CSS ── */
  var styleLink = document.createElement('link');
  styleLink.rel = 'stylesheet';
  styleLink.href = API + '/static/css/widget.css';
  document.head.appendChild(styleLink);

  /* ── Build HTML ── */
  var root = document.createElement('div');
  root.id = 'av-widget-root';
  document.body.appendChild(root);

  fetch(API + '/static/templates/widget.html')
    .then(function(res) { return res.text(); })
    .then(function(html) {
      root.innerHTML = html;
      initWidget();
    });

  function initWidget() {
    /* ── Set Logos ── */
    document.getElementById('av-hdr-logo').src = LOGO_SRC;
    document.getElementById('av-form-logo').src = LOGO_SRC;
    document.getElementById('av-ended-logo').src = LOGO_SRC;

    var isOpen = false, launcherOpen = false;
    // Pre-warm server when page loads
    setTimeout(function () {
      fetch(API + '/').catch(function () { });
    }, 1000);

    var uName = '', uEmail = '', uPhone = '';
    var sessId = '';
    fetch(API + '/api/session', {method: 'POST'}).then(function(r){return r.json();}).then(function(d){sessId=d.session_id;}).catch(function(){sessId='sess_'+Math.random().toString(36).slice(2);});
    var listening = false, recog = null;
    var msgCounter = 0, pollTimer = null, lastMsgId = 0;
    var isSending = false;
    var answeredIds = {};
    var syncInProgress = false; 
    var handoffTriggered = false; 

    /* ── Helpers ── */
    function $(id) { return document.getElementById(id); }

    function cleanMd(t) {
      return (t || '')
        .replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/https?:\/\/[^\s)]+/g, '')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '$1')
        .replace(/#{1,6}\s/g, '')
        .replace(/`(.*?)`/g, '$1')
        .replace(/\n/g, '<br>');
    }

    function scrl() {
      var m = $('av-msgs'); if (m) m.scrollTop = m.scrollHeight;
    }

    function shk(id) {
      var el = $(id); if (!el) return;
      el.style.borderColor = '#ef4444';
      el.style.animation = 'none'; el.offsetHeight;
      el.style.animation = 'av-shk .4s ease';
      setTimeout(function () { el.style.borderColor = ''; el.style.animation = ''; }, 800);
    }

    function getFallbackLink(txt) {
      var t = (txt || '').toLowerCase();
      if (t.includes('horoscope') || t.includes('moon sign')) return { label: '🌙 View Horoscope', url: SITE + '/horoscopes' };
      if (t.includes('consult')) return { label: '🔮 Talk to Astrologer', url: SITE + '/astrovedspeaks/' };
      if (t.trim().split(' ').length > 3) {
        return { label: '✨ Explore All Services', url: SITE + '/astrology-services' };
      }
      return null;
    }

    function createAvatar(type) {
      if (type === 'bot') return '<div class="av-av av-bot"><img src="' + LOGO_SRC + '" alt="bot"/></div>';
      return '<div class="av-av av-uav">' + (uName.slice(0, 2).toUpperCase() || 'ME') + '</div>';
    }

    function createBubble(type, content) {
      return '<div class="av-bbl av-' + type + '">' + content + '</div>';
    }

    /* ── Bot Message ── */
    function botMsg(txt, opts, link) {
      var m = $('av-msgs');
      var row = document.createElement('div');
      row.className = 'av-mrow av-bot';

      var linkHtml = '';
      if (link && link.url && link.label) {
        linkHtml = '<br><a class="av-link-btn" href="' + link.url + '" target="_blank" rel="noopener">' +
          '<svg viewBox="0 0 24 24"><path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg>' +
          link.label + '</a>';
      }
      var optsHtml = '';
      if (opts && opts.length) {
        optsHtml = '<div class="av-opt-btns">';
        opts.forEach(function (o) { optsHtml += '<button class="av-opt-btn">' + o + '</button>'; });
        optsHtml += '</div>';
      }
      row.innerHTML = createAvatar('bot') + createBubble('bot', cleanMd(txt) + linkHtml + optsHtml);

      if (optsHtml) {
        row.querySelectorAll('.av-opt-btn').forEach(function (b) {
          b.addEventListener('click', function () { doOpt(b); });
        });
      }
      m.appendChild(row); scrl();
    }

    /* ── User Message ── */
    function userMsg(txt) {
      var m = $('av-msgs');
      var row = document.createElement('div');
      row.className = 'av-mrow av-user';
      row.innerHTML = createBubble('user', cleanMd(txt)) + createAvatar('user');
      m.appendChild(row); scrl();
    }

    /* ── Support Card ── */
    function showSupportCard(txt) {
      var m = $('av-msgs');
      var row = document.createElement('div');
      row.className = 'av-mrow av-bot';

      var cardHtml = '<div class="av-bbl av-bot" style="border:1px solid rgba(201,168,76,0.6); background:rgba(201,168,76,.08);">' +
                     '<strong style="color:#E8C97A;font-family:\'Cinzel\',serif;">Need help from our support team?</strong><br><br>' +
                     cleanMd(txt) + '<br><br>' +
                     '<button class="av-sbtn" id="av-connect-support-btn" style="width:100%; margin-top:5px;">Connect to Support</button>' +
                     '</div>';

      row.innerHTML = createAvatar('bot') + cardHtml;
      m.appendChild(row); scrl();

      var btn = row.querySelector('#av-connect-support-btn');
      btn.addEventListener('click', function() {
        if (btn.disabled) return;
        btn.disabled = true;
        btn.innerHTML = 'Submitting...';
        
        fetch(API + '/api/handoff', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessId,
            user_name: uName,
            user_email: uEmail,
            user_phone: uPhone,
            issue_type: 'support_request',
            priority: 'normal'
          })
        }).then(function() {
          btn.innerHTML = '✓ Support request submitted<br><span style="font-size:10px; opacity:0.8;">Ref: ' + Math.floor(Math.random()*1000000) + '</span>';
          btn.style.background = '#22c55e';
          btn.style.color = '#fff';
          handoffTriggered = true;
          syncThenPoll();
        }).catch(function() {
          btn.disabled = false;
          btn.innerHTML = 'Failed. Try again.';
        });
      });
    }

    /* ── Typing ── */
    function showTyping() {
      var m = $('av-msgs');
      var r = document.createElement('div');
      r.className = 'av-mrow av-bot'; r.id = 'av-typ';
      r.innerHTML = createAvatar('bot') + createBubble('bot', '<div class="av-tbbl"><span></span><span></span><span></span></div>');
      m.appendChild(r); scrl();
    }
    function rmTyping() { var t = $('av-typ'); if (t) t.remove(); }

    /* ── Window Toggle ── */
    function toggleWin() {
      isOpen = !isOpen;
      $('av-win').classList.toggle('av-open', isOpen);
    }

    /* ── Launcher ── */
    function toggleLauncher() {
      if (isOpen) { toggleWin(); return; }
      launcherOpen = !launcherOpen;
      $('av-launcher-menu').classList.toggle('av-show', launcherOpen);
      $('av-launcher-fab').classList.toggle('av-open', launcherOpen);
      $('av-fab-msg').style.display = launcherOpen ? 'none' : '';
      $('av-fab-close').style.display = launcherOpen ? '' : 'none';
    }

    function closeLauncherMenu() {
      launcherOpen = false;
      $('av-launcher-menu').classList.remove('av-show');
      $('av-launcher-fab').classList.remove('av-open');
      $('av-fab-msg').style.display = '';
      $('av-fab-close').style.display = 'none';
    }

    function openSupportChat() {
      closeLauncherMenu();
      $('av-launcher-badge').style.display = 'none';
      if (!isOpen) toggleWin();
    }

    /* ── Start Chat (Form Submit) ── */
    function startChat() {
      var n = $('av-fn').value.trim();
      var e = $('av-fe').value.trim();
      var p = $('av-fp').value.trim();
      var cc = $('av-fcc').value;
      if (!n) { shk('av-fn'); return; }
      if (!e || !e.includes('@')) { shk('av-fe'); return; }
      if (!p || p.length < 7) { shk('av-fp'); return; }

      uName = n.split(' ')[0]; uEmail = e; uPhone = p;

      proceedToChat(uName);

      fetch(API + '/api/register', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessId, user_name: n, user_email: e, user_phone: p, country_code: cc })
      }).catch(function () { });
    }
    function proceedToChat(firstName) {
      var btn = $('av-start-btn');
      if (btn) { btn.innerHTML = '✦ &nbsp;Start Consulting'; btn.disabled = false; }
      $('av-fs').style.display = 'none';
      $('av-cs').classList.add('av-active');

      var m = $('av-msgs');
      var wc = document.createElement('div');
      wc.className = 'av-wcard';
      wc.innerHTML = '<div class="av-wcard-top">' +
        '<div class="av-wcard-av"><img src="' + LOGO_SRC + '" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" alt=""/></div>' +
        '<div class="av-wn">Namaste, ' + firstName + ' 🙏</div></div>' +
        '<p>✨ Welcome to AstroVed.AI — your personal Vedic cosmos companion. How may the stars guide your path?</p>';
      m.appendChild(wc);
      botMsg('The cosmos awaits, ' + firstName + '! What would you like to explore today?',
        ['🌙 Horoscope', '📊 Birth Chart', '💑 Compatibility', '❤️ Love', '🌿 Remedies'], null);
    }

    /* ── Send Message ── */
    function send() {
      if (isSending) return;

      var inp = $('av-inp');
      if (!inp) return;
      var txt = inp.value.trim();
      if (!txt) return;
      inp.value = ''; inp.style.height = '';

      msgCounter++;
      var reqId = msgCounter;
      userMsg(txt);

      isSending = true;
      $('av-send-btn').disabled = true;
      showTyping();
      callAPI(txt, 0, reqId);
    }


    function callAPI(txt, attempt, reqId) {
      setTimeout(function () {
        fetch(API + '/api/chat', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessId, message: txt })
        })
          .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
          .then(function (d) {
            isSending = false;
            $('av-send-btn').disabled = false;
            rmTyping();
            if (d.mode === 'with_agent') { handoffTriggered = true; syncThenPoll(); return; }
            if (d.mode === 'handoff_triggered') { handoffTriggered = true; botMsg(d.reply, [], null); syncThenPoll(); return; }
            if (d.mode === 'support_card') { showSupportCard(d.reply); return; }
            var link = (d.topic_url && d.topic_label)
              ? { url: d.topic_url, label: d.topic_label }
              : getFallbackLink(txt);
            botMsg(d.reply || 'Please try again.', [], link);
          })
          .catch(function () {
            if (attempt < 2) { setTimeout(function () { callAPI(txt, attempt + 1, reqId); }, 2000); }
            else {
              isSending = false;
              $('av-send-btn').disabled = false;
              rmTyping();
              botMsg('Server is waking up… Please resend in 30 seconds! 🔄', [], null);
            }
          });
      }, 200);
    }

    /* ── Polling ── */
    function startPolling() {
      if (pollTimer) return;
      pollTimer = setInterval(function () {
        fetch(API + '/api/poll/' + sessId + '?since_id=' + lastMsgId)
          .then(function (r) { return r.json(); })
          .then(function (d) {
            d.messages.forEach(function (m) {
              lastMsgId = Math.max(lastMsgId, m.id);
              if (answeredIds[m.id]) return;
              answeredIds[m.id] = true;
              $('av-send-btn').disabled = false;
              if (m.role === 'assistant') botMsg(m.content, [], null);
              else if (m.role === 'system') botMsg('🔔 ' + m.content, [], null);
            });
            if (d.status === 'closed' || d.status === 'bot') { clearInterval(pollTimer); pollTimer = null; }
          }).catch(function () { });
      }, 4000);
    }

    function syncThenPoll() {
      if (pollTimer) return;
      if (syncInProgress) return; 
      syncInProgress = true;
      fetch(API + '/api/poll/' + sessId + '?since_id=' + lastMsgId)
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.messages && d.messages.length) {
            d.messages.forEach(function (m) {
              lastMsgId = Math.max(lastMsgId, m.id);
              answeredIds[m.id] = true; 
            });
          }
          startPolling();
        })
        .catch(function () { startPolling(); })
        .finally(function () { syncInProgress = false; });
    }

    /* ── Opt Buttons ── */
    function doOpt(b) {
      var txt = b.textContent.trim();
      var container = b.closest('.av-opt-btns'); 
      if (container) container.remove();
      $('av-inp').value = txt;
      send();
    }

    /* ── CRM Panel ── */
    function showCRM() {
      handoffTriggered = true;
      var m = $('av-msgs');
      var row = document.createElement('div');
      row.className = 'av-mrow av-bot';
      row.innerHTML =
        createAvatar('bot') +
        createBubble('bot', 
        '🎧 <strong>Connect with Our Team</strong><br>Choose how you\'d like to reach us:' +
        '<div style="display:flex;flex-direction:column;gap:8px;margin-top:10px">' +
        '<a class="av-link-btn" style="justify-content:center" href="https://api.whatsapp.com/send?phone=919677391109&text=' + encodeURIComponent('Hello, I need assistance.') + '" target="_blank" rel="noopener">💬 WhatsApp — +91 96773 91109</a>' +
        '<a class="av-link-btn" style="justify-content:center" href="mailto:support@astroved.com">✉️ Email — support@astroved.com</a>' +
        '<a class="av-link-btn" style="justify-content:center" href="tel:+919677391108">📞 Call — +91 96773 91108</a>' +
        '</div>');
      m.appendChild(row);
      scrl();

      fetch(API + '/api/handoff', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessId,
          user_name: uName,
          user_email: uEmail,
          user_phone: uPhone,
          issue_type: 'support_request',
          priority: 'normal'
        })
      }).catch(function () { });

      syncThenPoll();
    }


    function backChat() {
      $('av-crm-panel').classList.remove('av-active');
      $('av-cs').classList.add('av-active');
    }

    /* ── End Chat ── */
    function showEnd() { $('av-eo').classList.add('av-show'); }
    function hideEnd() { $('av-eo').classList.remove('av-show'); }
    function doEnd() {
      hideEnd();
      $('av-cs').classList.remove('av-active');
      $('av-crm-panel').classList.remove('av-active');
      $('av-ended').classList.add('av-show');
    }

    /* ── Rating ── */
    var stars = document.querySelectorAll('.av-star');
    stars.forEach(function (s, i) {
      s.addEventListener('click', function () {
        stars.forEach(function (x, j) { x.classList.toggle('av-on', j <= i); });
        $('av-rt').style.display = 'block';
      });
    });

    /* ── Restart ── */
    function restart() {
      fetch(API + '/api/session', {method: 'POST'}).then(function(r){return r.json();}).then(function(d){sessId=d.session_id;}).catch(function(){sessId='sess_'+Math.random().toString(36).slice(2);});
      uName = ''; uEmail = ''; uPhone = '';
      msgCounter = 0; lastMsgId = 0;
      answeredIds = {};
      syncInProgress = false;
      handoffTriggered = false;
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
      $('av-ended').classList.remove('av-show');
      $('av-cs').classList.remove('av-active');
      $('av-crm-panel').classList.remove('av-active');
      $('av-fs').style.display = 'flex';
      $('av-msgs').innerHTML = '';
      ['av-fn', 'av-fe', 'av-fp'].forEach(function (id) { $(id).value = ''; });
      stars.forEach(function (s) { s.classList.remove('av-on'); });
      $('av-rt').style.display = 'none';
    }

    /* ── Voice ── */
    function toggleVoice() {
      if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        botMsg('Voice input needs Chrome browser.', [], null); return;
      }
      if (listening) { if (recog) recog.stop(); listening = false; $('av-vbtn').classList.remove('av-listening'); return; }
      var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      recog = new SR(); recog.lang = 'en-IN'; recog.interimResults = false;
      recog.onresult = function (e) { $('av-inp').value = e.results[0][0].transcript; listening = false; $('av-vbtn').classList.remove('av-listening'); send(); };
      recog.onerror = recog.onend = function () { listening = false; $('av-vbtn').classList.remove('av-listening'); };
      recog.start(); listening = true; $('av-vbtn').classList.add('av-listening');
    }

    /* ── Textarea auto-grow ── */
    function grow(el) { el.style.height = ''; el.style.height = Math.min(el.scrollHeight, 80) + 'px'; }

    /* ── Event Listeners ── */
    $('av-launcher-fab').addEventListener('click', toggleLauncher);
    $('av-support-opt').addEventListener('click', openSupportChat);
    $('av-wa-opt').addEventListener('click', function () {
      window.open('https://api.whatsapp.com/send?phone=919677391109&text=' + encodeURIComponent('Hello, I need help.'), '_blank');
      closeLauncherMenu();
    });
    $('av-min-btn').addEventListener('click', toggleWin);
    $('av-end-btn').addEventListener('click', showEnd);
    $('av-crm-btn').addEventListener('click', showCRM);
    $('av-eo-cancel').addEventListener('click', hideEnd);
    $('av-eo-confirm').addEventListener('click', doEnd);
    $('av-crm-back').addEventListener('click', backChat);
    $('av-restart-btn').addEventListener('click', restart);
    $('av-start-btn').addEventListener('click', startChat);
    $('av-send-btn').addEventListener('click', send);
    $('av-vbtn').addEventListener('click', toggleVoice);
    $('av-inp').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    $('av-inp').addEventListener('input', function () { grow(this); });
    $('av-fn').addEventListener('keydown', function (e) { if (e.key === 'Enter') $('av-fe').focus(); });
    $('av-fe').addEventListener('keydown', function (e) { if (e.key === 'Enter') $('av-fp').focus(); });
    $('av-fp').addEventListener('keydown', function (e) { if (e.key === 'Enter') startChat(); });

    document.addEventListener('click', function (e) {
      var l = $('av-launcher');
      if (launcherOpen && l && !l.contains(e.target)) closeLauncherMenu();
    });
  } // end initWidget

})();
