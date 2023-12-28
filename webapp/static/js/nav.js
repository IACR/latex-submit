function showSource(el) {
  let filename = el.dataset.filepath;
  if (filename in sources) {
    console.log('found source: ' + sources[filename]);
    fetch(sources[filename])
      .then(response => response.text())
      .then(data => {
        document.getElementById('sourcefile').innerHTML = data;
        const sourceTab = document.querySelector('button[data-bs-target="#nav-source"]')
        bootstrap.Tab.getOrCreateInstance(sourceTab).show()
        if ('filepath_line' in el.dataset) {
          let id = 'sourceline-' + String(el.dataset.filepath_line);
          let line = document.getElementById(id);
          if (line) {
            line.scrollIntoView({behavior: 'smooth'});
            document.querySelectorAll('div.highlight_log_line').forEach((el) => {
              el.classList.remove('highlight_log_line');
            });
            line.classList.add('highlight_log_line');
          } else {
            console.log('no line element');
          }
        } else {
          console.log('no line number')
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

function showPage(pageno) {
  let iframe = document.getElementById('pdfiframe');
  pdfurl = iframe.src;
  iframe.src = pdfurl.split('#')[0] + '#page=' + pageno;
  iframe.contentDocument.location.reload(true);
  const pdfTab = document.querySelector('button[data-bs-target="#nav-pdf"]')
  bootstrap.Tab.getOrCreateInstance(pdfTab).show()
}
function showLogLine(line) {
  const logTab = document.querySelector('button[data-bs-target="#nav-log"]')
  bootstrap.Tab.getOrCreateInstance(logTab).show()
  let logline = document.getElementById('logline-' + line);
  logline.scrollIntoView({behavior: 'smooth'});
  document.querySelectorAll('div.highlight_log_line').forEach((el) => {
    el.classList.remove('highlight_log_line');
  });
  logline.classList.add('highlight_log_line');
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
