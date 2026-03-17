# MATLAB Scientific Computing Guidelines

> Matrix operations, data I/O, plotting, and performance patterns for Anhui CIM project.

## Matrix Operations

### Creation

```matlab
A = [1 2 3; 4 5 6; 7 8 9];     % Literal
v = 1:0.1:10;                    % Range with step
v = linspace(0, 1, 100);         % N evenly spaced points
I = eye(n);                      % Identity
Z = zeros(m, n);                 % Zero matrix
O = ones(m, n);                  % Ones matrix
R = rand(m, n);                  % Uniform random
N = randn(m, n);                 % Normal random
```

### Key Operations

```matlab
B = A';                  % Transpose
C = A * B;               % Matrix multiply
D = A .* B;              % Element-wise multiply
x = A \ b;               % Solve Ax = b (preferred over inv(A)*b)
[V, D] = eig(A);         % Eigendecomposition
[U, S, V] = svd(A);      % SVD
```

**Rule**: Always use `A \ b` instead of `inv(A) * b` — more numerically stable and faster.

## Data I/O

### Tabular Data

```matlab
% Read
T = readtable('data.csv');
M = readmatrix('data.csv');

% Write
writetable(T, 'output.csv');
writematrix(M, 'output.csv');
```

### MAT Files (internal state)

```matlab
% Save specific variables
save('state.mat', 'busData', 'lineData', 'results');

% Load
load('state.mat');                    % All variables
S = load('state.mat', 'busData');     % Specific variable
```

### Python Exchange Formats

| Format | When |
|--------|------|
| CSV | Simple tabular data |
| Excel (.xlsx) | Data with headers, for reports |
| MAT | Complex arrays, internal MATLAB state |

```matlab
% Excel with sheet name
T = readtable('台账.xlsx', 'Sheet', 'Sheet1');
writetable(T, 'output.xlsx', 'Sheet', 'Results');
```

## Plotting

### Basic Patterns

```matlab
% Line plot
figure;
plot(x, y, 'b-', 'LineWidth', 1.5);
xlabel('Time (h)');
ylabel('Load (MW)');
title('Daily Load Curve');
grid on;

% Multiple series
hold on;
plot(x, y2, 'r--', 'LineWidth', 1.5);
legend('Feeder A', 'Feeder B', 'Location', 'best');
hold off;
```

### Bar Chart

```matlab
figure;
bar(categories, values);
xlabel('District');
ylabel('SAIDI (h/customer)');
```

### Saving Figures

```matlab
% PNG for reports
saveas(gcf, 'figures/result.png');

% PDF for publication
print('-dpdf', 'figures/result.pdf');

% High-DPI PNG
print('-dpng', '-r300', 'figures/result.png');
```

### Chinese Character Support

```matlab
% Set font that supports Chinese
set(gca, 'FontName', 'SimHei');
xlabel('时间 (小时)');
ylabel('负荷 (MW)');
```

## Performance Best Practices

### 1. Vectorize — avoid loops

```matlab
% BAD: loop
for i = 1:length(x)
    y(i) = sin(x(i)) * cos(x(i));
end

% GOOD: vectorized
y = sin(x) .* cos(x);
```

### 2. Preallocate arrays

```matlab
% BAD: growing array
for i = 1:1000
    results(i) = compute(i);
end

% GOOD: preallocated
results = zeros(1, 1000);
for i = 1:1000
    results(i) = compute(i);
end
```

### 3. Use logical indexing

```matlab
% BAD: loop with if
for i = 1:length(data)
    if data(i) > threshold
        filtered = [filtered; data(i)];
    end
end

% GOOD: logical indexing
filtered = data(data > threshold);
```

### 4. Avoid repeated file I/O in loops

```matlab
% BAD: read inside loop
for i = 1:n
    T = readtable(files{i});
    process(T);
end

% GOOD: read all then process
data = cell(n, 1);
for i = 1:n
    data{i} = readtable(files{i});
end
for i = 1:n
    process(data{i});
end
```

## Common Patterns for This Project

### Batch File Processing

```matlab
files = dir('data/*.csv');
results = cell(length(files), 1);

for i = 1:length(files)
    filepath = fullfile(files(i).folder, files(i).name);
    T = readtable(filepath);
    results{i} = analyze(T);
end

allResults = vertcat(results{:});
```

### Reliability Index Calculation

```matlab
% Typical pattern: load data, compute, export
lineData = readtable('line_params.csv');
busData = readmatrix('bus_data.csv');

% Vectorized computation
failureRate = lineData.length_km .* lineData.rate_per_km;
outageHours = failureRate .* lineData.repair_time;

% Export
resultTable = table(lineData.name, failureRate, outageHours, ...
    'VariableNames', {'LineName', 'FailureRate', 'OutageHours'});
writetable(resultTable, 'output/reliability_index.csv');
```

### Statistics Summary

```matlab
% Descriptive stats
m = mean(data);
s = std(data);
med = median(data);
[minVal, minIdx] = min(data);
[maxVal, maxIdx] = max(data);

% Group statistics
grouped = groupsummary(T, 'Category', 'mean', 'Value');
```

## SQLite / Database Toolbox

### 基本用法

```matlab
conn = sqlite(db_path, 'readonly');
cleanupObj = onCleanup(@() close(conn));  % 确保连接关闭
rows = fetch(conn, sql);                  % 返回 table 或 cell
```

### NULL 数值列处理

`fetch()` 遇到 NULL 数值列会直接崩溃（"Unexpected NULL"）。
**必须在 SQL 层用哨兵值替代 NULL**：

```matlab
% SQL 中：COALESCE(col, -1) 替代 NULL
% MATLAB 中：v >= 0 过滤哨兵值（跳过原 NULL 行）
if isnumeric(v) && ~isnan(v) && v >= 0
    map(key) = double(v);
end
```

### COALESCE 整数哨兵导致 int64 截断（高危）

`fetch()` 根据列内容推断类型。`COALESCE(col, -1)` 中 `-1` 是整数字面量，
当多数行值为整数（0 或 -1）时，整列被推断为 `int64`，**所有 REAL 小数被截断为 0**。

```matlab
% ❌ BAD — fetch 可能推断为 int64，0.065 → 0
sql = 'SELECT id, COALESCE(length, -1) FROM cable';

% ✅ GOOD — CAST 强制 REAL 类型
sql = 'SELECT id, CAST(COALESCE(length, -1) AS REAL) FROM cable';
```

**规则**：所有返回浮点数的 COALESCE 表达式必须包裹 `CAST(... AS REAL)`。
Python `sqlite3` 和 Java JDBC 不受影响（按行返回原始类型，不做列级推断）。

### R2022a+ string/missing 类型

`fetch()` 返回 `string` 类型（非 `char`），NULL 字符串为 `missing`：

```matlab
function c = ensure_cell(rows)
    if istable(rows), c = table2cell(rows); else, c = rows; end
    for i = 1:numel(c)
        if isstring(c{i})
            if ismissing(c{i}), c{i} = ''; else, c{i} = char(c{i}); end
        end
    end
end
```

### containers.Map 对应 Python dict

```matlab
m = containers.Map('KeyType','char','ValueType','double');
m(key) = value;  % 等价于 Python: d[key] = value
```

## Java Interop

### JAR Loading (deduplicated)

```matlab
if ~any(strcmp(javaclasspath('-dynamic'), jar_path))
    javaaddpath(jar_path);
end
```

### List\<Object[]\> → cell Conversion Template

```matlab
jList = javaObj.someList;
n = jList.size();
result = cell(n, ncols);
for i = 1:n
    row = jList.get(i - 1);  % Java 0-based
    for j = 1:ncols
        val = row(j);        % MATLAB 1-based on Java array
        if isempty(val) || (isjava(val) && isempty(char(val)))
            result{i, j} = '';
        elseif ischar(val) || isstring(val)
            result{i, j} = char(val);
        else
            result{i, j} = double(val);
        end
    end
end
```

### Rules

- `isjava(val)` already implies `isa(val, 'java.lang.Object')` — do not add redundant checks
- Java null appears as `[]` in MATLAB (`isempty` returns true)
- Loops at Java interop boundaries cannot be vectorized — this is an acceptable exception
- Each `parfor` worker has its own JVM; `javaaddpath` must run once per worker (dedup check ensures safety)
