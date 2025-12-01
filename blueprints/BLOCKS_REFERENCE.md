# Blueprint Editor - Referência de Blocos

## 📋 Categorias Disponíveis

### 🎮 **Chat** (2 blocos)
Comunicação com o chat das plataformas

- **Responder no chat** - Envia resposta simples
- **Enviar chat (plataforma)** - Envia mensagem para plataforma específica (Twitch/YouTube/Discord)

---

### 📊 **Data** (4 blocos)
Blocos de dados básicos

- **Texto** - Valor de texto constante
- **Número** - Valor numérico constante
- **Nome do usuário** - Retorna username de quem executou o comando
- **Formatar texto** - Concatena strings com template `{0}`, `{1}`, `{2}`

---

### 📝 **String** (11 blocos)
Manipulação avançada de texto

- **Concatenar Strings** - Une dois textos (`A + B`)
- **Tamanho do Texto** - Retorna o número de caracteres
- **Substring** - Extrai parte do texto (início, fim)
- **Contém Texto** - Verifica se texto contém substring
- **Substituir Texto** - Substitui ocorrências (`old` → `new`)
- **Dividir Texto** - Separa texto em lista usando separador
- **Maiúsculas** - Converte para UPPERCASE
- **Minúsculas** - Converte para lowercase
- **Remover Espaços** - Remove espaços no início/fim (trim)
- **Começa Com** - Verifica se texto inicia com prefixo
- **Termina Com** - Verifica se texto termina com sufixo

---

### 🔢 **Math** (13 blocos)
Operações matemáticas completas

- **Somar** - `A + B`
- **Multiplicação** - `A × B`
- **Subtração** - `A - B`
- **Divisão** - `A ÷ B`
- **Módulo** - Resto da divisão (`A % B`)
- **Potência** - `Base ^ Expoente`
- **Raiz Quadrada** - `√valor`
- **Valor Absoluto** - Remove sinal negativo
- **Mínimo** - Retorna o menor valor entre A e B
- **Máximo** - Retorna o maior valor entre A e B
- **Limitar Valor** - Mantém valor entre min e max (clamp)
- **Arredondar para Baixo** - Remove decimais (floor)
- **Arredondar para Cima** - Próximo inteiro acima (ceil)
- **Arredondar** - Arredonda para inteiro mais próximo

---

### 🧠 **Logic** (10 blocos)
Comparações e operações lógicas

**Comparadores:**
- **Maior que** - `A > B`
- **Menor que** - `A < B`
- **Igual** - `A == B`
- **Diferente** - `A != B`
- **Maior ou Igual** - `A ≥ B`
- **Menor ou Igual** - `A ≤ B`

**Operadores Booleanos:**
- **E lógico (AND)** - `A and B` - True se ambos são true
- **OU lógico (OR)** - `A or B` - True se pelo menos um é true
- **NÃO lógico (NOT)** - `not A` - Inverte valor
- **OU Exclusivo (XOR)** - `A xor B` - True se exatamente um é true

---

### 🔄 **Flow Control** (3 blocos)
Controle de fluxo de execução

- **Branch (Se/Então)** - Condicional com saídas True/False
- **Loop For** - Repete N vezes com índice (início, fim, passo)
- **Loop While** - Repete enquanto condição for verdadeira

---

### 📦 **Variables** (3 blocos)
Armazenamento de dados temporários

- **Obter Variável** - Lê valor de variável
- **Definir Variável** - Atribui valor a variável
- **Incrementar Variável** - Adiciona quantidade a variável (contador)

---

### 📋 **Array** (5 blocos)
Manipulação de listas/arrays

- **Criar Lista** - Cria array com até 4 itens
- **Obter Item da Lista** - Acessa elemento por índice
- **Tamanho da Lista** - Retorna número de elementos
- **Lista Contém** - Verifica se valor está na lista
- **Juntar Lista** - Converte array em string com separador

---

### 🔄 **Conversion** (3 blocos)
Conversão de tipos

- **Converter para Texto** - `str(valor)`
- **Converter para Número** - `int(valor)`
- **Converter para Boolean** - `bool(valor)`

---

### 🎲 **Random** (3 blocos)
Geração de valores aleatórios

- **Número Aleatório** - Inteiro aleatório entre min e max
- **Escolha Aleatória** - Escolhe opção aleatória de lista separada por vírgulas
- **Boolean Aleatório** - True/False baseado em % de chance (0-100)

---

### ⏰ **Time** (3 blocos)
Operações de tempo

- **Aguardar** - Pausa execução por N segundos (delay)
- **Timestamp Atual** - Retorna timestamp Unix atual
- **Data/Hora Atual** - Retorna data/hora formatada (strftime)

---

### ⌨️ **Macros** (1 bloco)
Automação de teclado

- **Macro: pressionar teclas** - Simula pressionamento de teclas (wasd, etc)

---

### 💰 **Points** (3 blocos)
Sistema de pontos

- **Pontos: obter** - Consulta pontos do usuário
- **Pontos: adicionar** - Adiciona pontos
- **Pontos: remover** - Remove pontos

---

### 🎵 **Audio** (5 blocos)
Controle de áudio/TTS

- **Audio: TTS** - Text-to-Speech em vários idiomas
- **Audio: tocar** - Reproduz arquivo de áudio
- **Audio: parar** - Para reprodução atual
- **Audio: limpar fila** - Limpa fila de reprodução
- **Audio: tamanho da fila** - Retorna número de itens na fila

---

### 🗳️ **Voting** (5 blocos)
Sistema de votação/enquetes

- **Votação: iniciar** - Cria enquete com opções e duração
- **Votação: obter ativa** - Pega ID da votação ativa
- **Votação: votar** - Registra voto em opção
- **Votação: encerrar** - Finaliza votação
- **Votação: resultados** - Obtém resultados da votação

---

### 🎮 **Minigames** (1 bloco)
Integração com sistema de minijogos

- **Minigame: comando** - Executa comando de minijogo

---

## 🎨 Tipos de Dados

- **exec** - Fluxo de execução (conexões brancas)
- **string** - Texto (conexões verdes)
- **number** - Números (conexões azuis)
- **bool** - Booleano True/False (conexões vermelhas)
- **array** - Listas/arrays (conexões laranjas)
- **any** - Qualquer tipo (conexões roxas)

---

## 🔗 Características dos Blocos

### Blocos Puros (isPure: true)
- Não têm entrada/saída de execução (exec)
- Apenas processam e retornam dados
- Podem ser conectados a qualquer campo compatível
- Exemplo: Math, String, Logic, Data

### Blocos de Ação
- Possuem fluxo de execução (exec in/out)
- Executam operações com efeitos colaterais
- Exemplo: Chat, Audio, Points, Variables

### Blocos de Controle
- Possuem múltiplas saídas de execução
- Controlam o fluxo do programa
- Exemplo: Branch, For Loop, While Loop

---

## 💡 Dicas de Uso

1. **Composição de Dados**: Conecte blocos puros em cadeia para criar expressões complexas
2. **Variáveis**: Use variáveis para armazenar resultados temporários entre blocos
3. **Loops**: Combine loops com variáveis para criar contadores e iterações
4. **Random**: Use blocos random para criar comportamentos variados e dinâmicos
5. **String Operations**: Combine concatenação, formatação e substituição para mensagens dinâmicas
6. **Arrays**: Crie listas de opções e use random_choice para seleção aleatória
7. **Conversão**: Use conversão de tipos quando conectar blocos de tipos diferentes

---

## 📚 Total de Blocos: **78 blocos**

O editor de blueprints agora possui capacidades equivalentes a programação Python completa, incluindo:
- ✅ Operações matemáticas avançadas
- ✅ Manipulação completa de strings
- ✅ Arrays e listas
- ✅ Variáveis e estado
- ✅ Controle de fluxo (if/else, loops)
- ✅ Operações lógicas booleanas
- ✅ Aleatoriedade
- ✅ Tempo e delays
- ✅ Conversão de tipos
- ✅ Integração completa com sistema de bot (chat, áudio, pontos, votação, minijogos)
