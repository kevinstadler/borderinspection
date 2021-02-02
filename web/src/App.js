import { useEffect, useMemo, useState } from 'react';
import { useExpanded, useGroupBy, useSortBy, useTable } from 'react-table';

function App() {
  const [data, setData] = useState([]);
  useEffect(() => {
    fetch('data.csv').then((res) => {
      res.text().then((txt) => {
        const [names, ...lines] = txt.trim().split("\n").map((line) => line.split(';'));
        const xs = lines.map((line) => Object.fromEntries(line.map((value, i) => [names[i], i >= 3 ? parseFloat(value) : value])));
        setData(xs);
      });
    });
  }, []);

  const twoDigits = (n) => n < .01 ? n.toPrecision(1) : n.toFixed(2);

  const columns = useMemo(() => 
    [
      {
        accessor: 'iso'
      },
      {
        Header: 'Country',
        accessor: 'name',
        aggregate: 'first',
      },
      {
        Header: 'Parts',
        aggregate: 'count',
      },
      {
        Header: 'Border length',
        accessor: 'perimeter',
        Cell: (p) => twoDigits(p.value) + ' km',
        aggregate: 'sum',
      },
/*      {
        Header: 'Area',
        accessor: 'area',
        sortDescFirst: true,
        Cell: (p) => twoDigits(p.value) + ' km²',
        aggregate: 'sum',
      },*/
      {
        Header: 'Holes',
        accessor: 'holes',
        aggregate: 'first',
      },
      {
        Header: '📼',
        accessor: 'videos',
        Cell: (p) => p.value ? <>{p.value.split(' ').map(id => <a href={'https://youtu.be/' + id}>📼</a>)}</> : '',
        aggregate: 'first',
      },
    ], []);

  const tableInstance = useTable({
      columns,
      data,
      initialState: {
        hiddenColumns: ['iso'],
        groupBy: ['iso'],
        sortBy: [
          { id: 'iso' },
          { id: 'perimeter', desc: true },
          { id: 'holes', desc: true },
          { id: 'Parts', desc: true },
          { id: 'videos', desc: true },
          { id: 'name' },
        ]
      },
//      isMultiSortEvent: () => true,
//      disableSortRemove: true,
      defaultCanSort: true, // to allow sorting by aggregated 'nparts'
      aggregations: { first: (leaves, agg) => leaves[0] }
    }, useGroupBy, useSortBy, useExpanded);

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
    setSortBy,
    state: { sortBy }
  } = tableInstance;

  // id of the newly designated 'sortedIndex=0' column
  const prependToMultiSort = (designatedColumn) => {
//    const newTop = sortBy.findIndex((el) => el.id == designatedColumn.id);
    // ugly to mangle the state directly but what gives let's see
//    console.log(sortBy.findIndex((el) => el.id.equalsIgnoreCase(designatedColumn.id)));
    sortBy.sort((a, b) => a.id === designatedColumn.id ? -1 : b.id === designatedColumn.id ? 1 : 0);
    if (designatedColumn.sortedIndex === 0) {
      sortBy[0].desc = !sortBy[0].desc;
    }
    setSortBy(sortBy);
    // get current state
//    const sortBy = headerGroups.map(headerGroup => headerGroup.headers.map((column) => { id: column.id, desc: column.isSortedDesc } ));
//    const sortedIndices = headerGroups.map(headerGroup => headerGroup.headers.map((column) => column.sortedIndex));
//    sortedIndices[newtop] = -1;
//    sortBy.sort((a, b) => ); // negative for a < b
//    console.log(cur.map((dummy, i) => ));
//    isSortedDesc
//    setSortBy([{id: X, desc: X}]);
  };

  // for intercepting sort clicks
//  const onClickSortByAll = (first, isSortedDesc) => {
//    toggleSortBy(first, !isSortedDesc, false); // or isSortedDesc === undefined
//    if (first != 'perimeter') {
//      toggleSortBy('perimeter', true, true);
//    }
//  };
  //, onClick: () => onClickSortByAll(column.id, column.isSortedDesc)

  return (
    <div className="App">
  <table {...getTableProps()}>
    <thead>
      {// Loop over the header rows
      headerGroups.map(headerGroup => (
        // Apply the header row props
        <tr {...headerGroup.getHeaderGroupProps()}>
          {// Loop over the headers in each row
          headerGroup.headers.map(column => (
            <th {...column.getHeaderProps(column.getSortByToggleProps({ title: 'Sort By ' + column.Header, onClick: () => prependToMultiSort(column) }))}>
              {column.render('Header')}{column.isSorted && column.sortedIndex === 0 ? (column.isSortedDesc ? ' ▼' : ' ▲') : ''}
            </th>
          ))}
        </tr>
      ))}
      </thead>
     {/* Apply the table body props */}
     <tbody {...getTableBodyProps()}>
       {// Loop over the table rows
       rows.map(row => {
         // Prepare the row for display
         prepareRow(row)
         return (
           // Apply the row props
           <tr {...row.getRowProps()}>
             {// Loop over the rows cells
             row.cells.map((cell, i) => {
               // Apply the cell props
               return (
                 <td {...cell.getCellProps()}>
                      {i === 0 ? ( cell.isAggregated ? 
                        row.subRows.length === 1 ? <>{'▹ '}{cell.render('Cell')}</> : 
                        // If it's a grouped cell, add an expander
                        <>
                          <span {...row.getToggleRowExpandedProps()}>
                            { row.isExpanded ? '▾' : '▸'}{' '}{cell.render('Cell')}
                          </span>
                          
                        </> : ""
                      ) : cell.isAggregated ? (
                        // If the cell is aggregated, use the Aggregated
                        // renderer for cell
                        cell.render('Aggregated')
                      ) : cell.isPlaceholder ? null : ( // For cells with repeated values, render null
                        // Otherwise, just render the regular cell
                        cell.render('Cell')
                      )}
               </td>
               )
             })}
           </tr>
         )
       })}
     </tbody>
   </table>
    </div>
  );
}

export default App;
