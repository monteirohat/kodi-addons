<p align="center">
  <img src="repository.monteiromedia/resources/icon.png" alt="Monteiro" width="140">
</p>

<h1 align="center">Monteiro</h1>

<p align="center">
  Add-ons práticos e de código aberto para Kodi, LibreELEC e Raspberry Pi.<br>
  Assista canais e filmes de listas M3U, veja suas fotos e arquivos e controle sua central de mídia do sofá.
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
4. Abra **Instalar via repositório > Monteiro** e instale os add-ons que quiser. O Easy Channel e o Easy Movie ficam em **Add-ons de vídeo**, o HDMI Switcher e o Easy Files em **Add-ons de programas**, e o Easy Picture em **Add-ons de imagens**.

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
  <tr>
    <td align="center" width="33%">
      <a href="script.easy.files/README.md"><img src="script.easy.files/resources/icon.png" alt="Easy Files" width="120"></a>
      <h3>Easy Files</h3>
      Um gerenciador de arquivos para o controle: copie, mova, renomeie e apague com um toque longo.
      <br><br>
      <a href="#easy-files">Resumo</a> · <a href="script.easy.files/README.md">Guia</a>
    </td>
    <td align="center" width="33%">
      <a href="script.easy.picture/README.md"><img src="script.easy.picture/resources/icon.png" alt="Easy Picture" width="120"></a>
      <h3>Easy Picture</h3>
      Suas fotos em galeria, por álbum, e cada uma em tela cheia com um toque no OK.
      <br><br>
      <a href="#easy-picture">Resumo</a> · <a href="script.easy.picture/README.md">Guia</a>
    </td>
    <td align="center" width="33%">
      <a href="skin.monteiro/README.md"><img src="skin.monteiro/resources/icon.png" alt="Skin Monteiro" width="120"></a>
      <h3>Skin Monteiro</h3>
      Uma tela inicial e menus no mesmo visual, com cada add-on Easy a um toque.
      <br><br>
      <a href="#skin-monteiro">Resumo</a> · <a href="skin.monteiro/README.md">Guia</a>
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
- Segure o **OK** num grupo para renomeá-lo ou excluí-lo.
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

### Easy Files

<img src="script.easy.files/resources/icon.png" alt="Easy Files" width="72" align="left">

**Um gerenciador de arquivos para o controle remoto.** Os locais à esquerda, a pasta à direita e todas as opções a um toque longo.

<br clear="left">

- A sua pasta pessoal, pendrives, compartilhamentos de rede e as pastas do Kodi, com o espaço livre de cada disco.
- Segure o **OK** num arquivo ou pasta para abrir, renomear, copiar, mover ou apagar, criar uma pasta ou ver os detalhes.
- As cópias mostram o progresso e podem ser canceladas.

![Easy Files](script.easy.files/resources/screenshots/screenshot-01.jpg)

Leia o [guia do Easy Files](script.easy.files/README.md) para conhecer cada recurso. O guia está em inglês.

### Easy Picture

<img src="script.easy.picture/resources/icon.png" alt="Easy Picture" width="72" align="left">

**Suas fotos na TV, em galeria.** Os álbuns à esquerda, as fotos do álbum à direita e cada foto em tela cheia com um toque no OK.

<br clear="left">

- Todas as imagens e as suas favoritas primeiro, e depois um álbum para cada pasta de fotos.
- Esquerda e Direita passam as fotos em tela cheia.
- Segure o **OK** numa foto para marcá-la como favorita, girá-la ou espelhá-la, ou ver a data, o tamanho, a resolução e a pasta.

![Easy Picture](script.easy.picture/resources/screenshots/screenshot-01.jpg)

Leia o [guia do Easy Picture](script.easy.picture/README.md) para conhecer cada recurso. O guia está em inglês.

> [!NOTE]
> O Easy Channel e o Easy Movie não oferecem nenhum conteúdo. Eles tocam as listas M3U que você adiciona, e você é responsável por usar só listas que tem permissão para assistir. Os repositórios sugeridos do GitHub reúnem canais gratuitos e públicos e filmes em domínio público, e são mantidos por terceiros.

## Skin Monteiro

Um skin para o Kodi no visual dos add-ons, sob a licença MIT. A tela inicial abre direto os add-ons Easy, e as configurações, menus, teclado e barras do player seguem o mesmo visual escuro, com o foco em azul aço. Instale em **Monteiro > Aparência > Skin**.

![Tela inicial do skin Monteiro](.github/assets/monteiro-skin.jpg)

- **TV**, **Filmes** e **Séries** abrem o Easy Channel e o Easy Movie, **Imagens** abre o Easy Picture e **Arquivos** abre o Easy Files. Sem o add-on, o item oferece a instalação.
- **Vídeos** e **Música** abrem as fontes do Kodi, e **Add-ons** abre os add-ons instalados, com uma barra para busca, repositórios e atualizações.
- Os botões no canto superior direito abrem as configurações de Wi-Fi do LibreELEC, as configurações do Kodi e o menu de energia.

Leia o [guia do skin](skin.monteiro/README.md), em inglês, para conhecer cada tela.

## Ajuda e sugestões

- Encontrou um problema? Abra um [relato de bug](https://github.com/monteirohat/kodi-addons/issues/new?template=bug_report.yml).
- Tem uma ideia? Abra uma [sugestão](https://github.com/monteirohat/kodi-addons/issues/new?template=feature_request.yml).
- Dúvidas, dicas e listas que funcionam bem ficam nas [Discussions](https://github.com/monteirohat/kodi-addons/discussions).

Os formulários de bug e de sugestão estão em inglês, mas você pode escrever em português.

Para montar o repositório, publicar atualizações ou mudar um add-on, leia o [CONTRIBUTING.md](CONTRIBUTING.md), em inglês.

## Licença

MIT. Veja [LICENSE](LICENSE).
