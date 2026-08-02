function Mudar_imagem(Nome_div,Img_Num,Imagem_src){
    var foto = document.getElementById(Nome_div);
    foto.innerHTML = '<a href='+Imagem_src+' target="_blank"><img src='+Imagem_src+' /></a>';
}

function search (quantidade,cidade,religiao,nacao,regente,fundacao) {
	for(i=0;i<quantidade;i++) {
		var aux;
		var action;
		
		showdiv(i);
		
		//cidade	
		if((document.getElementById('cid_'+i).innerHTML.toLowerCase() != cidade.toLowerCase()) && (cidade != ''))
			hidediv(i);
		
		//religiao
		action = 0;
		aux = document.getElementById('rel_'+i).innerHTML.split(', ');
		for(j=0;j<aux.length;j++){
			if((aux[j] != religiao) && (religiao != ''))
				action--;
			else
				action += 1*aux.length;
		}
		if (action < 0)	
			hidediv(i);		
		
		//nacao
		action = 0;
		aux = document.getElementById('nac_'+i).innerHTML.split(', ');
		for(j=0;j<aux.length;j++){
			if((aux[j] != nacao) && (nacao != ''))
				action--;
			else
				action += 1*aux.length;
		}
		if (action < 0)	
			hidediv(i);	
			
		//regente
		action = 0;
		aux = document.getElementById('reg_'+i).innerHTML.split(', ');
		for(j=0;j<aux.length;j++){
			if((aux[j].toLowerCase() != regente.toLowerCase()) && (regente != ''))
				action--;
			else
				action += 1*aux.length;
		}
		if (action < 0)	
			hidediv(i);	
            	
		//fundacao
		if((document.getElementById('fun_'+i).innerHTML != fundacao) && (fundacao != ''))
			hidediv(i);
	}
	
	if(document.getElementById('terreiros').offsetHeight < '400')
			showdiv('nenhum');
	else
			hidediv('nenhum');
}

function limpar () {
	document.getElementById('cidade').value = '';
	document.getElementById('religiao').value = '';
	document.getElementById('nacao').value = '';
	document.getElementById('regente').value = '';	
	document.getElementById('fundacao').value = '';	
}