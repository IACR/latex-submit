function showSource(el) {
  let filename = el.dataset.filepath;
  console.log('filename=' + filename)
  if (filename in sources) {
    console.log('found source: ' + sources[filename]);
    fetch(sources[filename])
      .then(response => response.text())
      .then(data => {
        document.getElementById('sourcefile').innerHTML = data;
        const sourceTab = document.querySelector('button[data-bs-target="#nav-source"]')
        bootstrap.Tab.getOrCreateInstance(sourceTab).show()
        var id = 'sourceline-1'; // default if there is no filepath_line number in the error.
        if ('filepath_line' in el.dataset) {
          id = 'sourceline-' + String(el.dataset.filepath_line);
        } else {
          console.log('no line number')
        }
        let line = document.getElementById(id);
        if (line) {
          line.scrollIntoView({behavior: 'smooth'});
          document.querySelectorAll('div.highlight_log_line').forEach((el) => {
            el.classList.remove('highlight_log_line');
          });
          if (id != 'sourceline-1') {
            line.classList.add('highlight_log_line');
          }
        } else {
          console.log('no line element');
        }
      })
  } else {
    console.log('source not found');
    fetch(allSources)
      .then(response=>response.text())
      .then(data => {
        document.getElementById('sourcefile').innerHTML = data;
      });
  }
}

function reload_iframe(el, src) {
  el.src = src;
  if (el.contentDocument != null) {
    // firefox may have this as null.
    el.contentDocument.location.reload(true);
  }
}

/*
 * This is called to scroll the PDF(s) to a given page. The only way
 * to do this is to reload the iframe with a new fragment. Browsers
 * will often block reloading if only the hash segment of a URL changes,
 * so we also rely upon the server sending a different eTag and a cache
 * limit of 0 seconds. Without that it was impossible to get firefox to
 * reload.
*/
function showPage(pageno) {
  let iframe = document.getElementById('pdfiframe');
  let pdfurl = iframe.src;
  let args = '#view=FitH&page=' + pageno;
  reload_iframe(iframe, pdfurl.split('#')[0] + args);
  // For view of final PDF, there are two iframes to scroll.
  let orig_iframe = document.getElementById('orig_pdf_iframe');
  if (orig_iframe) {
    let orig_pdfurl = orig_iframe.src;
    reload_iframe(orig_iframe, orig_pdfurl.split('#')[0] + args);
  }
  const pdfTab = document.querySelector('button[data-bs-target="#nav-pdf"]')
  bootstrap.Tab.getOrCreateInstance(pdfTab).show()
}
function showLogLine(error_type, line) {
  const logTab = document.querySelector('button[data-bs-target="#nav-log"]')
  bootstrap.Tab.getOrCreateInstance(logTab).show()
  console.log('line='+line);
  let id = 'logline-' + line;
  if (error_type == 'bibtex') {
    id = 'bibtex-' + line;
  }
  console.log('id='+id);
  let logline = document.getElementById(id);
  logline.scrollIntoView({behavior: 'smooth'});
  document.querySelectorAll('div.highlight_log_line').forEach((el) => {
    el.classList.remove('highlight_log_line');
  });
  logline.classList.add('highlight_log_line');
}
function scrollToBibtex(id) {
  if (id) {
    console.log(id);
    bibentry = document.getElementById('bibtex:' + id);
    if (bibentry) {
      const inputTab = document.querySelector('button[data-bs-target="#nav-source"]');
      bootstrap.Tab.getOrCreateInstance(inputTab).show();
      bibentry.scrollIntoView({behavior: 'smooth'});
    }
  }
}

function showWhere(elem) {
  let data = elem.dataset;
  if ('pageno' in data) {
    console.log('page is ' + data.pageno);
    let pdfTab = document.getElementById('nav-pdf');
    if (pdfTab) {
      let embed = pdfTab.children[0];
      console.log('old embedUrl is ' + embed.src);
      let embedUrl = embed.src.split('#')[0] + '#page=' + data.pageno;
      console.log('new embedUrl is ' + embedUrl);
      embed.src = embedUrl;
      embed.contentDocument.location.reload(true);
    }
  }
  console.log(elem);
}
function showHTML() {
  const htmlTab = document.querySelector('button[data-bs-target="#nav-html"]')
    bootstrap.Tab.getOrCreateInstance(htmlTab).show()
}
function showMeta() {
  const metaTab = document.querySelector('button[data-bs-target="#nav-meta"]')
  bootstrap.Tab.getOrCreateInstance(metaTab).show()
}   
