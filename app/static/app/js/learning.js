(() => {
  const tracker = document.getElementById('lesson-study-tracker');
  if (!tracker) return;

  const csrfToken = document.querySelector(
    '#learning-csrf-form [name="csrfmiddlewaretoken"]'
  )?.value;
  if (!csrfToken) return;

  let watchedSeconds = Number(tracker.dataset.watchedSeconds || 0);
  let studyInFlight = false;
  let videoInFlight = false;

  const postProgress = async (url, values = {}, keepalive = false) => {
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      body: new URLSearchParams(values),
      keepalive,
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
      },
    });
    if (!response.ok) throw new Error('Progress request failed');
    return response.json();
  };

  const revealLesson = (lessonId) => {
    const lessonLink = document.getElementById(`lesson-${lessonId}`);
    if (!lessonLink || lessonLink.dataset.unlocked === 'true') return;

    lessonLink.dataset.unlocked = 'true';
    lessonLink.href = lessonLink.dataset.openHref;
    lessonLink.removeAttribute('aria-disabled');
    lessonLink.removeAttribute('tabindex');
    lessonLink.classList.remove('text-muted');

    const icon = lessonLink.querySelector('[data-status-icon]');
    if (icon) icon.className = 'bi bi-play-circle me-2';

    const badge = lessonLink.querySelector('[data-lock-badge]');
    if (badge) {
      badge.textContent = 'Đã mở khóa';
      badge.className = 'badge bg-success-subtle text-success';
      badge.removeAttribute('data-lock-badge');
    }
    lessonLink.querySelector('[data-lock-description]')?.remove();
  };

  const applyCompletion = (progress) => {
    if (progress.next_lesson_unlocked && progress.next_lesson_id) {
      revealLesson(progress.next_lesson_id);
      const nextStatus = document.getElementById('study-time-status');
      if (nextStatus) {
        nextStatus.textContent = 'Bài tiếp theo đã được mở khóa.';
        nextStatus.closest('.alert')?.classList.replace('alert-primary', 'alert-success');
      } else {
        const nextAlert = document.querySelector('#lesson-completion-status')?.previousElementSibling;
        if (nextAlert?.classList.contains('alert')) {
          nextAlert.innerHTML = '<i class="bi bi-unlock-fill me-2"></i>Bài tiếp theo đã được mở khóa.';
          nextAlert.classList.replace('alert-primary', 'alert-success');
        }
      }
    }

    if (!progress.completed) return;

    document.getElementById('lesson-completed-badge')?.removeAttribute('hidden');

    const status = document.getElementById('lesson-completion-status');
    if (status) {
      status.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>Bài học đã hoàn thành.';
      status.classList.remove('text-muted');
      status.classList.add('text-success');
    }

    const videoStatus = document.getElementById('video-watch-status');
    if (videoStatus) {
      videoStatus.textContent = 'Đã đạt yêu cầu xem video. Bài học đã hoàn thành.';
      videoStatus.classList.replace('alert-info', 'alert-success');
    }

    const currentLesson = document.querySelector('#courseAccordion .active [data-status-icon]');
    if (currentLesson) currentLesson.className = 'bi bi-check-circle-fill me-2';

    const progressBar = document.querySelector('[role="progressbar"] .progress-bar');
    const progressLabel = document.querySelector('[role="progressbar"]')?.nextElementSibling;
    if (typeof progress.course_progress === 'number' && progressBar) {
      progressBar.style.width = `${progress.course_progress}%`;
      progressBar.parentElement.setAttribute('aria-valuenow', progress.course_progress);
      if (progressLabel) progressLabel.textContent = `Tiến độ khóa học: ${progress.course_progress}%`;
    }

    if (progress.current_streak !== undefined) {
      const streakCount = document.getElementById('learning-streak-count');
      if (streakCount) streakCount.textContent = progress.current_streak;
    }
    if (progress.longest_streak !== undefined) {
      const streakBest = document.getElementById('learning-streak-best');
      if (streakBest) streakBest.textContent = progress.longest_streak;
    }

  };

  document.querySelectorAll('#courseAccordion a[data-unlocked="false"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      if (link.dataset.unlocked !== 'true') event.preventDefault();
    });
  });

  const sendStudyHeartbeat = async (allowHidden = false, endSession = false) => {
    if (studyInFlight || (!allowHidden && document.visibilityState !== 'visible')) return;
    studyInFlight = true;

    try {
      const progress = await postProgress(
        tracker.dataset.url,
        endSession ? { end_session: '1' } : {},
        endSession,
      );
      watchedSeconds = progress.watched_seconds;

      const status = document.getElementById('study-time-status');
      if (status) {
        if (progress.next_lesson_unlocked) {
          status.textContent = 'Bài tiếp theo đã được mở khóa.';
          status.closest('.alert')?.classList.replace('alert-primary', 'alert-success');
        } else {
          const minutes = Math.floor(watchedSeconds / 60);
          const seconds = watchedSeconds % 60;
          status.textContent = `Thời gian học đã tích lũy: ${minutes} phút ${seconds} giây.`;
        }
      }

      if (progress.next_lesson_unlocked && progress.next_lesson_id) {
        revealLesson(progress.next_lesson_id);
      }
    } catch (_error) {
      // A later heartbeat retries after a brief connection problem.
    } finally {
      studyInFlight = false;
    }
  };

  if (tracker.dataset.lessonType !== 'VIDEO') {
    let studyTimer = window.setInterval(sendStudyHeartbeat, 15000);
    sendStudyHeartbeat();

    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        sendStudyHeartbeat(true, true);
        window.clearInterval(studyTimer);
      } else {
        sendStudyHeartbeat();
        studyTimer = window.setInterval(sendStudyHeartbeat, 15000);
      }
    });
  }

  const recordNonVideoCompletion = async (source) => {
    try {
      const progress = await postProgress(tracker.dataset.completionUrl, { source });
      applyCompletion(progress);
    } catch (_error) {
      // The learner can repeat the reading/open action if the request failed.
    }
  };

  if (tracker.dataset.lessonType === 'ARTICLE') {
    const marker = document.getElementById('article-end-marker');
    if (marker && 'IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          observer.disconnect();
          recordNonVideoCompletion('article_read');
        }
      }, { threshold: 1 });
      observer.observe(marker);
    }
  }

  if (tracker.dataset.lessonType === 'DOCUMENT') {
    document.getElementById('lesson-attachment-link')?.addEventListener('click', () => {
      recordNonVideoCompletion('document_opened');
    });
  }

  const videoFrame = document.getElementById('lesson-video-player');
  if (
    !videoFrame
    || tracker.dataset.lessonType !== 'VIDEO'
    || tracker.dataset.videoProvider !== 'youtube'
  ) return;

  const playerUrl = new URL(videoFrame.src);
  playerUrl.searchParams.set('enablejsapi', '1');
  playerUrl.searchParams.set('origin', window.location.origin);
  videoFrame.src = playerUrl.toString();

  let videoPlayer = null;
  let videoTimer = null;

  const reportVideoProgress = async () => {
    if (videoInFlight || !videoPlayer || document.visibilityState !== 'visible') return;

    const duration = videoPlayer.getDuration();
    const position = videoPlayer.getCurrentTime();
    if (!duration || !Number.isFinite(duration) || !Number.isFinite(position)) return;

    videoInFlight = true;
    try {
      const progress = await postProgress(tracker.dataset.videoUrl, {
        position: String(position),
        duration: String(duration),
      });
      const watchStatus = document.getElementById('video-watch-status');
      if (watchStatus && !progress.completed) {
        watchStatus.textContent = `Đã xem ${progress.watched_percent}% · Tự động hoàn thành khi đạt ${tracker.dataset.videoThreshold}% video.`;
      }
      const studyStatus = document.getElementById('study-time-status');
      if (studyStatus && !progress.next_lesson_unlocked) {
        const minutes = Math.floor(progress.watched_seconds / 60);
        const seconds = progress.watched_seconds % 60;
        studyStatus.textContent = `Thời gian video đã xem: ${minutes} phút ${seconds} giây.`;
      }
      applyCompletion(progress);
      if (progress.completed) stopVideoHeartbeats();
    } catch (_error) {
      // The next player heartbeat reports its current position again.
    } finally {
      videoInFlight = false;
    }
  };

  const startVideoHeartbeats = () => {
    if (videoTimer) window.clearInterval(videoTimer);
    reportVideoProgress();
    videoTimer = window.setInterval(reportVideoProgress, 5000);
  };

  const stopVideoHeartbeats = () => {
    if (videoTimer) window.clearInterval(videoTimer);
    videoTimer = null;
  };

  const initializeYouTubePlayer = () => {
    videoPlayer = new window.YT.Player(videoFrame, {
      events: {
        onReady: reportVideoProgress,
        onStateChange: (event) => {
          if (event.data === window.YT.PlayerState.PLAYING) {
            startVideoHeartbeats();
          } else {
            stopVideoHeartbeats();
            if (event.data === window.YT.PlayerState.ENDED) reportVideoProgress();
          }
        },
      },
    });
  };

  if (window.YT?.Player) {
    initializeYouTubePlayer();
  } else {
    window.onYouTubeIframeAPIReady = initializeYouTubePlayer;
    const apiScript = document.createElement('script');
    apiScript.src = 'https://www.youtube.com/iframe_api';
    apiScript.async = true;
    document.head.appendChild(apiScript);
  }
})();
