/**
 * RAPR AI Browser Tools — Content Script
 *
 * Runs in each page context, providing DOM access for browser automation
 * tools: read_page, click, type_text, find_element, get_page_text,
 * extract_table, fill_form.
 */

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleAction(message)
    .then((result) => sendResponse(result))
    .catch((err) => sendResponse({ error: String(err) }));
  return true;  // async response
});


async function handleAction(message) {
  const { action } = message;

  switch (action) {
    case "read_page":
      return readPage();

    case "click":
      return clickElement(message.selector);

    case "type_text":
      return typeText(message.selector, message.text);

    case "find_element":
      return findElement(message.description);

    case "get_page_text":
      return getPageText();

    case "extract_table":
      return extractTable(message.selector);

    case "fill_form":
      return fillForm(message.fields);

    default:
      throw new Error(`Unknown content action: ${action}`);
  }
}


// ---------------------------------------------------------------------------
// Tool implementations
// ---------------------------------------------------------------------------

/**
 * Read a simplified representation of the page — headings, links, buttons,
 * inputs, images, and key text.  Much smaller than raw HTML.
 */
function readPage() {
  const elements = [];
  const seen = new Set();

  // Headings
  document.querySelectorAll("h1, h2, h3").forEach((el) => {
    const text = el.innerText.trim();
    if (text && !seen.has(text)) {
      seen.add(text);
      elements.push({ type: el.tagName.toLowerCase(), text });
    }
  });

  // Links
  document.querySelectorAll("a[href]").forEach((el) => {
    const text = el.innerText.trim();
    if (text && text.length < 200) {
      elements.push({
        type: "link",
        text,
        href: el.href,
        selector: generateSelector(el),
      });
    }
  });

  // Buttons
  document.querySelectorAll("button, [role='button'], input[type='submit'], input[type='button']").forEach((el) => {
    const text = (el.innerText || el.value || el.getAttribute("aria-label") || "").trim();
    if (text) {
      elements.push({
        type: "button",
        text,
        selector: generateSelector(el),
        disabled: el.disabled || false,
      });
    }
  });

  // Form inputs
  document.querySelectorAll("input, textarea, select").forEach((el) => {
    if (el.type === "hidden") return;
    const label = getInputLabel(el);
    elements.push({
      type: "input",
      input_type: el.type || el.tagName.toLowerCase(),
      label,
      name: el.name || "",
      value: el.value || "",
      placeholder: el.placeholder || "",
      selector: generateSelector(el),
    });
  });

  // Images with alt text
  document.querySelectorAll("img[alt]").forEach((el) => {
    const alt = el.alt.trim();
    if (alt) {
      elements.push({ type: "image", alt, src: el.src });
    }
  });

  return {
    url: window.location.href,
    title: document.title,
    element_count: elements.length,
    elements: elements.slice(0, 200),  // cap at 200 elements
  };
}


function clickElement(selector) {
  const el = document.querySelector(selector);
  if (!el) throw new Error(`Element not found: ${selector}`);

  // Scroll into view and click
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.click();
  return { ok: true, text: (el.innerText || "").slice(0, 100) };
}


function typeText(selector, text) {
  const el = document.querySelector(selector);
  if (!el) throw new Error(`Element not found: ${selector}`);

  el.focus();
  el.value = text;
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  return { ok: true };
}


function findElement(description) {
  const desc = description.toLowerCase();
  const candidates = document.querySelectorAll(
    "button, a, input, select, textarea, [role='button'], [role='link'], [role='tab']"
  );

  const results = [];
  candidates.forEach((el) => {
    const text = (
      el.innerText ||
      el.value ||
      el.placeholder ||
      el.getAttribute("aria-label") ||
      el.title ||
      ""
    ).toLowerCase();

    const name = (el.name || el.id || el.className || "").toLowerCase();

    if (text.includes(desc) || name.includes(desc)) {
      const rect = el.getBoundingClientRect();
      const visible = rect.width > 0 && rect.height > 0;
      if (visible) {
        results.push({
          tag: el.tagName.toLowerCase(),
          text: (el.innerText || el.value || el.placeholder || "").slice(0, 100),
          selector: generateSelector(el),
          type: el.type || "",
        });
      }
    }
  });

  if (results.length === 0) {
    throw new Error(`No element found matching: "${description}"`);
  }

  return { matches: results.slice(0, 10) };
}


function getPageText() {
  let text = document.body.innerText || "";
  // Truncate to 50KB
  if (text.length > 50000) {
    text = text.slice(0, 50000) + "\n...(truncated)";
  }
  return {
    url: window.location.href,
    title: document.title,
    text,
    length: text.length,
  };
}


function extractTable(selector) {
  const table = document.querySelector(selector);
  if (!table) throw new Error(`Table not found: ${selector}`);

  // Get headers
  const headers = [];
  table.querySelectorAll("th").forEach((th) => {
    headers.push(th.innerText.trim());
  });

  // Get rows
  const rows = [];
  table.querySelectorAll("tr").forEach((tr) => {
    const cells = tr.querySelectorAll("td");
    if (cells.length === 0) return;

    const row = {};
    cells.forEach((td, i) => {
      const key = headers[i] || `col_${i}`;
      row[key] = td.innerText.trim();
    });
    rows.push(row);
  });

  return { headers, rows, row_count: rows.length };
}


function fillForm(fields) {
  const results = {};

  for (const [selector, value] of Object.entries(fields)) {
    const el = document.querySelector(selector);
    if (!el) {
      results[selector] = { ok: false, error: "Element not found" };
      continue;
    }

    try {
      if (el.tagName === "SELECT") {
        el.value = value;
        el.dispatchEvent(new Event("change", { bubbles: true }));
      } else if (el.type === "checkbox" || el.type === "radio") {
        el.checked = !!value;
        el.dispatchEvent(new Event("change", { bubbles: true }));
      } else {
        el.focus();
        el.value = value;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }
      results[selector] = { ok: true };
    } catch (err) {
      results[selector] = { ok: false, error: String(err) };
    }
  }

  return results;
}


// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Generate a CSS selector that uniquely identifies an element.
 */
function generateSelector(el) {
  if (el.id) return `#${CSS.escape(el.id)}`;

  // Try name attribute for form elements
  if (el.name) {
    const byName = document.querySelectorAll(`[name="${CSS.escape(el.name)}"]`);
    if (byName.length === 1) return `[name="${el.name}"]`;
  }

  // Try aria-label
  const ariaLabel = el.getAttribute("aria-label");
  if (ariaLabel) {
    const byAria = document.querySelectorAll(`[aria-label="${CSS.escape(ariaLabel)}"]`);
    if (byAria.length === 1) return `[aria-label="${ariaLabel}"]`;
  }

  // Fall back to tag + nth-of-type
  const parent = el.parentElement;
  if (parent) {
    const siblings = Array.from(parent.children).filter(
      (c) => c.tagName === el.tagName
    );
    const index = siblings.indexOf(el) + 1;
    const parentSel = parent.id ? `#${CSS.escape(parent.id)}` : parent.tagName.toLowerCase();
    return `${parentSel} > ${el.tagName.toLowerCase()}:nth-of-type(${index})`;
  }

  return el.tagName.toLowerCase();
}


/**
 * Try to find a label for a form input.
 */
function getInputLabel(el) {
  // Explicit <label for="...">
  if (el.id) {
    const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
    if (label) return label.innerText.trim();
  }

  // Implicit <label><input></label>
  const parent = el.closest("label");
  if (parent) {
    const text = parent.innerText.trim();
    if (text) return text;
  }

  // aria-label
  const ariaLabel = el.getAttribute("aria-label");
  if (ariaLabel) return ariaLabel;

  // placeholder
  if (el.placeholder) return el.placeholder;

  return el.name || "";
}
