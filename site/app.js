const state = {
  jobs: [],
  filteredJobs: [],
  bookmarks: new Set(JSON.parse(localStorage.getItem("internship-bookmarks") || "[]")),
  bookmarksOnly: false,
  metadata: null,
};

const els = {
  jobsTableBody: document.getElementById("jobs-table-body"),
  emptyState: document.getElementById("empty-state"),
  categoryFilter: document.getElementById("category-filter"),
  typeFilter: document.getElementById("type-filter"),
  sortFilter: document.getElementById("sort-filter"),
  searchInput: document.getElementById("search-input"),
  bookmarkToggle: document.getElementById("bookmark-toggle"),
  resultsCount: document.getElementById("results-count"),
  updatedAt: document.getElementById("updated-at"),
  totalJobs: document.getElementById("total-jobs"),
  newJobs: document.getElementById("new-jobs"),
  trackedCompanies: document.getElementById("tracked-companies"),
};

async function loadJobsPayload() {
  const candidates = ["./jobs.json", "../jobs.json"];
  for (const url of candidates) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        continue;
      }
      return response.json();
    } catch (error) {
      console.debug(`Unable to fetch ${url}`, error);
    }
  }
  throw new Error("Unable to load jobs.json");
}

function normalizeTypeLabel(type) {
  const value = (type || "").toLowerCase();
  if (value.includes("unpaid")) {
    return "unpaid";
  }
  if (value.includes("paid") || value.includes("stipend")) {
    return "paid";
  }
  return "mixed";
}

function isNew(job) {
  if (!job.first_seen_at) {
    return false;
  }
  const firstSeen = new Date(job.first_seen_at);
  return Date.now() - firstSeen.getTime() <= 24 * 60 * 60 * 1000;
}

function formatTimestamp(value) {
  if (!value) {
    return "Updated date unavailable";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function compactText(value, maxLength = 80) {
  const text = (value || "").trim();
  if (text.length <= maxLength) {
    return text || "Not specified";
  }
  return `${text.slice(0, maxLength - 1)}...`;
}

function isReasonableTitle(title) {
  const value = (title || "").trim();
  if (!value) {
    return false;
  }
  if (value.length > 140) {
    return false;
  }
  if (value.split(/\s+/).length > 18) {
    return false;
  }

  const lower = value.toLowerCase();
  const blockedFragments = [
    "privacy",
    "terms",
    "investor relations",
    "log in",
    "login",
    "register",
    "cookie",
    "site map",
    "sitemap",
    "complaint",
  ];
  return !blockedFragments.some((fragment) => lower.includes(fragment));
}

function sortJobs(jobs, mode) {
  const sorted = [...jobs];
  sorted.sort((left, right) => {
    if (mode === "company") {
      return left.company.localeCompare(right.company);
    }
    if (mode === "title") {
      return left.title.localeCompare(right.title);
    }
    return new Date(right.first_seen_at || right.scraped_at || 0) - new Date(left.first_seen_at || left.scraped_at || 0);
  });
  return sorted;
}

function updateFilters() {
  const query = els.searchInput.value.trim().toLowerCase();
  const category = els.categoryFilter.value;
  const type = els.typeFilter.value;

  const filtered = state.jobs.filter((job) => {
    const searchable = `${job.title} ${job.company} ${job.location} ${job.category}`.toLowerCase();
    const matchesQuery = !query || searchable.includes(query);
    const matchesCategory = !category || job.category === category;
    const matchesType = !type || normalizeTypeLabel(job.type) === type;
    const matchesBookmark = !state.bookmarksOnly || state.bookmarks.has(job.id);
    return matchesQuery && matchesCategory && matchesType && matchesBookmark;
  });

  state.filteredJobs = sortJobs(filtered, els.sortFilter.value);
  renderJobs();
}

function saveBookmarks() {
  localStorage.setItem("internship-bookmarks", JSON.stringify([...state.bookmarks]));
}

function toggleBookmark(jobId) {
  if (state.bookmarks.has(jobId)) {
    state.bookmarks.delete(jobId);
  } else {
    state.bookmarks.add(jobId);
  }
  saveBookmarks();
  updateFilters();
}

function renderJobs() {
  els.jobsTableBody.innerHTML = "";
  els.resultsCount.textContent = `${state.filteredJobs.length} matches`;
  els.emptyState.classList.toggle("hidden", state.filteredJobs.length !== 0);

  for (const job of state.filteredJobs) {
    const row = document.createElement("tr");

    const bookmarkCell = document.createElement("td");
    const bookmarkButton = document.createElement("button");
    bookmarkButton.type = "button";
    bookmarkButton.className = "bookmark-button";
    bookmarkButton.textContent = state.bookmarks.has(job.id) ? "Saved" : "Save";
    bookmarkButton.setAttribute("aria-label", "Bookmark internship");
    bookmarkButton.addEventListener("click", () => toggleBookmark(job.id));
    bookmarkCell.appendChild(bookmarkButton);

    const titleCell = document.createElement("td");
    titleCell.className = "title-cell";
    titleCell.title = job.title;
    titleCell.textContent = compactText(job.title, 90);
    if (isNew(job)) {
      const badge = document.createElement("span");
      badge.className = "new-badge";
      badge.textContent = "New";
      titleCell.appendChild(document.createTextNode(" "));
      titleCell.appendChild(badge);
    }

    const companyCell = document.createElement("td");
    companyCell.textContent = compactText(job.company, 40);

    const locationCell = document.createElement("td");
    locationCell.textContent = compactText(job.location || "Not specified", 30);

    const categoryCell = document.createElement("td");
    categoryCell.textContent = compactText(job.category, 24);

    const typeCell = document.createElement("td");
    typeCell.textContent = compactText(job.type, 16);

    const sourceCell = document.createElement("td");
    sourceCell.textContent = compactText(job.source, 16);

    const addedCell = document.createElement("td");
    addedCell.textContent = isNew(job) ? "Last 24h" : formatTimestamp(job.first_seen_at);

    const applyCell = document.createElement("td");
    const applyLink = document.createElement("a");
    applyLink.href = job.apply_link;
    applyLink.target = "_blank";
    applyLink.rel = "noopener noreferrer";
    applyLink.className = "apply-link";
    applyLink.textContent = "Open";
    applyCell.appendChild(applyLink);

    row.append(
      bookmarkCell,
      titleCell,
      companyCell,
      locationCell,
      categoryCell,
      typeCell,
      sourceCell,
      addedCell,
      applyCell
    );

    els.jobsTableBody.appendChild(row);
  }
}

function populateCategoryFilter(jobs) {
  const categories = [...new Set(jobs.map((job) => job.category).filter(Boolean))].sort((left, right) =>
    left.localeCompare(right)
  );
  for (const category of categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    els.categoryFilter.appendChild(option);
  }
}

function renderStats(payload) {
  const jobs = payload.jobs || [];
  const stats = payload.stats || {};
  els.totalJobs.textContent = stats.total_jobs ?? jobs.length;
  els.newJobs.textContent = stats.new_jobs_last_24h ?? jobs.filter(isNew).length;
  els.trackedCompanies.textContent = stats.total_companies ?? 0;
  els.updatedAt.textContent = payload.generated_at
    ? `Last refreshed ${formatTimestamp(payload.generated_at)}`
    : "Last refresh unavailable";
}

async function boot() {
  try {
    const payload = await loadJobsPayload();
    const jobs = Array.isArray(payload) ? payload : payload.jobs || [];
    state.metadata = payload;
    state.jobs = jobs.filter((job) => isReasonableTitle(job.title));

    populateCategoryFilter(state.jobs);
    renderStats(
      Array.isArray(payload)
        ? { jobs: state.jobs }
        : {
            ...payload,
            jobs: state.jobs,
            stats: {
              ...(payload.stats || {}),
              total_jobs: state.jobs.length,
              new_jobs_last_24h: state.jobs.filter(isNew).length,
            },
          }
    );
    updateFilters();
  } catch (error) {
    els.updatedAt.textContent = "Unable to load jobs feed.";
    els.emptyState.classList.remove("hidden");
    els.emptyState.textContent = "The internships feed could not be loaded.";
    console.error(error);
  }
}

els.searchInput.addEventListener("input", updateFilters);
els.categoryFilter.addEventListener("change", updateFilters);
els.typeFilter.addEventListener("change", updateFilters);
els.sortFilter.addEventListener("change", updateFilters);
els.bookmarkToggle.addEventListener("click", () => {
  state.bookmarksOnly = !state.bookmarksOnly;
  els.bookmarkToggle.classList.toggle("active", state.bookmarksOnly);
  els.bookmarkToggle.textContent = state.bookmarksOnly ? "Showing bookmarks" : "Show bookmarks only";
  updateFilters();
});

boot();
