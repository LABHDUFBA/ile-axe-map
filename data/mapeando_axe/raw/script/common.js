function _(id) {
	return document.getElementById(id);
}


function show_submenu(id) {
	if (_('submenu' + id))
		_('submenu' + id).style.display = 'block';
}

function hide_submenu(id) {
	if (_('submenu' + id))
		_('submenu' + id).style.display = 'none';
}


function externalLinks() {
	if (!document.getElementsByTagName) return;
	var anchors = document.getElementsByTagName("a");
	for (var i=0; i<anchors.length; i++) {
		var anchor = anchors[i];
		if (anchor.getAttribute("href") && anchor.getAttribute("rel") == "external") {
			anchor.target = "_blank";
		}
	}
}
window.onload = externalLinks;


function checkBrowser() {
	browser = navigator.appName;
	if (browser.indexOf("Microsoft")!=-1)
	{
		version = navigator.appVersion;
		if (version.indexOf("MSIE 6.0")!=-1)
		{
			alert('A versão de seu Internet Explorer é inferior à exigida pelo site. Favor atualizar seu navegador para visualizar corretamente.');
		}
	}
}

function hidediv(id) {
	//safe function to hide an element with a specified id
	if (document.getElementById) { // DOM3 = IE5, NS6
		document.getElementById(id).style.display = 'none';
	}
	else {
		if (document.layers) { // Netscape 4
			document.id.display = 'none';
		}
		else { // IE 4
			document.all.id.style.display = 'none';
		}
	}
}

function showdiv(id) {
	//safe function to show an element with a specified id
		  
	if (document.getElementById) { // DOM3 = IE5, NS6
		document.getElementById(id).style.display = 'block';
	}
	else {
		if (document.layers) { // Netscape 4
			document.id.display = 'block';
		}
		else { // IE 4
			document.all.id.style.display = 'block';
		}
	}
}