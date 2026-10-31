# Radar de vagas

Aplicação local em Streamlit que reúne vagas de tecnologia, identifica tecnologias citadas nas descrições e compara a demanda com as habilidades cadastradas pelo usuário.

## Funcionalidades

- Importação de vagas pelas APIs públicas do [Remotive](https://remotive.com/remote-jobs/api) e do [Arbeitnow](https://www.arbeitnow.com/job-board-api).
- Persistência local de vagas e habilidades em SQLite (`.data/radar_vagas.db`).
- Busca por cargo, empresa e descrição, além de filtros por tecnologia, nível e modalidade.
- Filtro por localidade e tradução sob demanda do título e da descrição para português pelo Microsoft Translator.
- Extração de habilidades por um vocabulário de tecnologias conhecido.
- Gráfico das tecnologias mais citadas e sugestões de habilidades ainda não cadastradas no seu perfil.
- Perfil local com nome, cargo desejado, habilidades da lista e habilidades personalizadas.

Os níveis e as habilidades são inferidos por correspondência de termos, não por análise semântica. Vagas podem não informar nível, e a classificação de modalidade depende dos dados disponibilizados pela fonte. O Remotive lista vagas remotas; as demais modalidades dependem dos registros do Arbeitnow.

## Executar

Requer Python 3.10 ou superior.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Abra o endereço local mostrado pelo Streamlit e clique em **Atualizar vagas** para consultar as APIs. A aplicação precisa de acesso à internet para importar vagas; o conteúdo já importado continua disponível localmente.

## Tradução de vagas

A tradução é opcional e feita sob demanda: abra **Descrição completa** e clique em **Traduzir título e descrição para português**. O texto público da vaga é enviado ao Microsoft Translator; a tradução fica salva no banco local para reutilização. O serviço pode cobrar pelo uso.

Configure a chave do recurso Microsoft Translator no ambiente antes de iniciar o Streamlit. No PowerShell:

```powershell
$env:AZURE_TRANSLATOR_KEY = "sua-chave"
$env:AZURE_TRANSLATOR_REGION = "sua-regiao"
python -m streamlit run app.py
```

`AZURE_TRANSLATOR_REGION` pode ser omitida quando o recurso não exigir uma região. A chave não deve ser colocada no código nem compartilhada.

## Testes

```powershell
python -m pytest
```

Para salvar o banco em outro local, defina `RADAR_DB_PATH` antes de executar a aplicação.
