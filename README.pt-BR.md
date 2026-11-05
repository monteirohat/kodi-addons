<p align="center">
  <img src="repository.monteiromedia/resources/icon.png" alt="Monteiro" width="140">
</p>

<h1 align="center">Monteiro</h1>

<p align="center">
  Add-ons práticos e de código aberto para Kodi, LibreELEC e Raspberry Pi.<br>
  Assista canais e filmes de listas M3U do jeito fácil e controle sua central de mídia do sofá.
</p>

<p align="center">
  <a href="README.md">English</a> · <b>Português (Brasil)</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Kodi-21%20Omega-17B2E7" alt="Kodi 21 Omega">
  <img src="https://img.shields.io/badge/LibreELEC-12.2-3B8BFF" alt="LibreELEC 12.2">
  <img src="https://img.shields.io/badge/licen%C3%A7a-MIT-22272E" alt="Licença MIT">
  <a href="https://github.com/monteirohat/kodi-addons/releases"><img src="https://img.shields.io/github/downloads/monteirohat/kodi-addons/total?label=downloads&color=3B8BFF" alt="Downloads das releases"></a>
  <a href="https://github.com/monteirohat/kodi-addons/stargazers"><img src="https://img.shields.io/github/stars/monteirohat/kodi-addons?label=estrelas&color=FFC53D" alt="Estrelas no GitHub"></a>
</p>

<p align="center">
  <img src=".github/assets/easy-channel.gif" alt="Easy Channel: troca de grupos, um canal que não responde e a oferta de removê-lo" width="860"><br>
  <sub>Easy Channel: troque de grupo, abra um canal que não responde e remova-o num passo só, com <b>Verificar o canal antes de abrir</b> ligado.</sub>
</p>

<p align="center">
  <a href="#instalação">Instalação</a> ·
  <a href="#add-ons">Add-ons</a> ·
  <a href="#ajuda-e-sugestões">Ajuda e sugestões</a> ·
  <a href="CONTRIBUTING.md">Como contribuir</a>
</p>

## Instalação

Registre o repositório **Monteiro** no Kodi uma vez, pelo endereço web, e todos os add-ons e atualizações passam a ser instalados por ele.

1. No Kodi, abra **Configurações > Sistema > Add-ons** e ligue **Fontes desconhecidas**.
2. Abra **Configurações > Gerenciador de arquivos > Adicionar fonte**, selecione **&lt;Nenhum&gt;**, digite `https://monteirohat.github.io/kodi-addons/`, dê o nome **Monteiro** à fonte e selecione **OK**.
3. Abra **Configurações > Add-ons > Instalar via arquivo zip > Monteiro** e selecione **repository.monteiromedia-1.0.5.zip**. Espere o aviso de que o repositório **Monteiro** foi instalado.
4. Abra **Instalar via repositório > Monteiro** e instale os add-ons que quiser. O Easy Channel e o Easy Movie ficam em **Add-ons de vídeo**, e o HDMI Switcher em **Add-ons de programas**.

As atualizações chegam pelo repositório. Se uma ainda não aparecer, abra o menu de contexto do **Monteiro** e selecione **Verificar atualizações**. Se o aparelho com Kodi estiver sem internet, baixe o ZIP na [última release](https://github.com/monteirohat/kodi-addons/releases/latest), copie para um pendrive e use **Instalar via arquivo zip**.

## Add-ons

<table>
  <tr>
    <td align="center" width="33%">
      <a href="script.m3u.channels/README.md"><img src="script.m3u.channels/resources/icon.png" alt="Easy Channel" width="120"></a>
      <h3>Easy Channel</h3>
      TV ao vivo de listas M3U numa tela no estilo de TV box, que mantém só os canais que funcionam.
      <br><br>
      <a href="#easy-channel">Resumo</a> · <a href="script.m3u.channels/README.md">Guia</a>
    </td>
    <td align="center" width="33%">
      <a href="script.m3u.movies/README.md"><img src="script.m3u.movies/resources/icon.png" alt="Easy Movie" width="120"></a>
      <h3>Easy Movie</h3>
      Os filmes e séries das suas listas M3U num catálogo de pôsteres, com temporadas e Continuar assistindo.
      <br><br>
      <a href="#easy-movie">Resumo</a> · <a href="script.m3u.movies/README.md">Guia</a>
    </td>
    <td align="center" width="33%">
      <a href="script.hdmi.switcher/README.md"><img src="script.hdmi.switcher/resources/hdmi-switcher-icon.png" alt="HDMI Switcher" width="120"></a>
      <h3>HDMI Switcher</h3>
      Escolha a tela HDMI ativa de um Raspberry Pi 4 direto pelo Kodi.
      <br><br>
      <a href="#hdmi-switcher">Resumo</a> · <a href="script.hdmi.switcher/README.md">Guia</a>
    </td>
  </tr>
</table>

### Easy Channel

<img src="script.m3u.channels/resources/icon.png" alt="Easy Channel" width="72" align="left">

**Adicione uma lista M3U em poucos passos, navegue pelos canais por grupo e remova os que param de funcionar assim que falham.** Não precisa configurar playlist nem EPG.

<br clear="left">

- Grupos à esquerda, canais no meio e os detalhes do canal em foco à direita.
- Listas por endereço web, por arquivo ou pelos arquivos M3U de um repositório do GitHub, com sugestões de repositórios de canais gratuitos e públicos.
- Quando um canal não abre, o Easy Channel oferece removê-lo, e **Verificar canais** testa um grupo inteiro de uma vez.
- Um grupo de **Favoritos** no topo, busca em todas as listas e exportação de um arquivo M3U limpo.
- Selecionar **TV** no menu principal do Kodi abre o Easy Channel.

![Easy Channel](script.m3u.channels/resources/screenshots/screenshot-01.jpg)

Leia o [guia do Easy Channel](script.m3u.channels/README.md) para conhecer cada recurso e ajuste. O guia está em inglês.

### Easy Movie

<img src="script.m3u.movies/resources/icon.png" alt="Easy Movie" width="72" align="left">

**Transforme os filmes e séries das suas listas M3U num catálogo de pôsteres.** Abra um filme para ver os detalhes, ou uma série para escolher a temporada e continuar de onde parou.

<br clear="left">

- Gêneros à esquerda e seis pôsteres por linha, com título e duração.
- Episódios agrupados em séries automaticamente, com temporadas, episódios, marca de assistido e um botão **Continuar**.
- Um grupo **Continuar assistindo**, e filmes e episódios retomam de onde você parou.
- Controles do player no estilo dos apps de streaming, com pulos de 10 segundos, legendas e faixas de áudio, e legendas do OpenSubtitles ligadas automaticamente no seu idioma.
- Listas por endereço web, por arquivo ou do GitHub, com um repositório sugerido de filmes em domínio público.
- O mesmo gerenciador de listas, verificação, favoritos e detecção de falhas do Easy Channel, no mesmo visual.
- Pastas com os seus próprios vídeos, no cartão SD, em pendrives ou em compartilhamentos de rede, com pôsteres e detalhes do Cinemeta.
- Um catálogo dos filmes e séries do Cinemeta, com **Minha lista**, e addons do Stremio adicionados pelo endereço, cujas fontes vão para um gerenciador de downloads de torrent ou tocam na hora.
- Com a biblioteca vazia, selecionar **Filmes** ou **Seriados** no menu principal do Kodi abre o Easy Movie.

<img src=".github/assets/easy-movie.gif" alt="Easy Movie: gêneros, pôsteres, detalhes do filme e o catálogo do Cinemeta" width="860">

Leia o [guia do Easy Movie](script.m3u.movies/README.md) para conhecer cada recurso e ajuste. O guia está em inglês.

### HDMI Switcher

<img src="script.hdmi.switcher/resources/hdmi-switcher-icon.png" alt="HDMI Switcher" width="72" align="left">

**Alterne entre uma tela HDMI pequena e um monitor externo sem usar a linha de comando.** Escolha a tela, e o Kodi reinicia nela.

<br clear="left">

- Dois cartões de tela que mostram qual está ativa e quais estão conectadas, no mesmo visual escuro do Easy Channel e do Easy Movie.
- Feito para o LibreELEC no Raspberry Pi 4, com a tela pequena em `HDMI-A-1` e o monitor externo em `HDMI-A-2`.
- Mantém as suas configurações avançadas e faz uma cópia do arquivo de configuração antes da primeira mudança.
- Lembra a tela escolhida nas próximas vezes que o Kodi iniciar.

![HDMI Switcher](script.hdmi.switcher/resources/screenshots/screenshot-01.jpg)

O HDMI Switcher precisa de uma [configuração única](script.hdmi.switcher/README.md#one-time-setup), que remove ajustes antigos de HDMI na inicialização. Leia o [guia do HDMI Switcher](script.hdmi.switcher/README.md) para os detalhes. O guia está em inglês.

> [!NOTE]
> O Easy Channel e o Easy Movie não oferecem nenhum conteúdo. Eles tocam as listas M3U que você adiciona, e você é responsável por usar só listas que tem permissão para assistir. Os repositórios sugeridos do GitHub reúnem canais gratuitos e públicos e filmes em domínio público, e são mantidos por terceiros.

## Ajuda e sugestões

- Encontrou um problema? Abra um [relato de bug](https://github.com/monteirohat/kodi-addons/issues/new?template=bug_report.yml).
- Tem uma ideia? Abra uma [sugestão](https://github.com/monteirohat/kodi-addons/issues/new?template=feature_request.yml).
- Dúvidas, dicas e listas que funcionam bem ficam nas [Discussions](https://github.com/monteirohat/kodi-addons/discussions).

Os formulários de bug e de sugestão estão em inglês, mas você pode escrever em português.

Para montar o repositório, publicar atualizações ou mudar um add-on, leia o [CONTRIBUTING.md](CONTRIBUTING.md), em inglês.

## Licença

MIT. Veja [LICENSE](LICENSE).
