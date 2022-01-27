import { useEffect, useMemo, useState } from 'react';
import { useExpanded, useSortBy, useTable } from 'react-table';

const parseRows = (string, colNames = undefined) => {
  const data = string.trim().split("\n").map((line) => line.split(';'));
  if (colNames === undefined) {
    colNames = data[0];
    data.shift();
  }
  return data.map((row) => Object.fromEntries(row.map((value, i) => [colNames[i], i >= 3 ? parseFloat(value) : value])));
}

function App() {
  const [loadedCountries, setLoadedCountries] = useState([]);
  const [data, setData] = useState([]);
  useEffect(() => {
    fetch('data/data.csv').then((res) => {
      res.text().then((txt) => {
        setData(parseRows(txt).map((obj) => { return { ...obj, subRows: [{name: 'Loading parts...'}] } }));
      });
    });
  }, []);
  // is this necessary??
//  const tableData = useMemo(() => data, loadedCountries);

  const getCountry = (row) => {
    if (loadedCountries.includes(row.index)) {
      row.getToggleRowExpandedProps().onClick();
    } else {
      row.toggleRowExpanded(true);
      fetch('data/' + row.allCells[0].value + '.csv').then((res) => {
        res.text().then((txt) => {
          setLoadedCountries([parseInt(row.id), ...loadedCountries]);
          const newData = [ ...data ];
          newData[row.id] = { ...data[row.id], subRows: parseRows(txt, Object.keys(data[0])) }
          console.log(newData[row.id]);
          setData(newData);
          // gotta do this again for some reason...
          row.toggleRowExpanded(true);
        });
      });
    }
}

//  const twoDigits = (n) => n < .01 ? n.toPrecision(1) : n.toFixed(2);
  const unitIfValue = (value, unit) => value ? value + unit : '';

  const columns = useMemo(() => 
    [
      {
        accessor: 'iso'
      },
      {
        Header: 'Full Name',
        accessor: 'name',
        Cell: (p) => {
//          console.log(p);
          return p.value;
        }
      },
      {
        Header: '# Parts',
        accessor: 'nparts',
        Cell: (p) => isNaN(p.value) ? '' : p.value,
      },
      {
        Header: '# Holes',
        accessor: 'holes',
      },
      {
        Header: 'Border Length',
        accessor: 'perimeter',
        Cell: (p) => unitIfValue(p.value, ' km'),
      },
/*      {
        Header: 'Area',
        accessor: 'area',
        sortDescFirst: true,
        Cell: (p) => unitIfValue(p.value, ' km²'),
      },*/
      {
        Header: '📼',
        accessor: 'videos',
        Cell: (p) => p.value ? <span>{p.value.split(' ').map(id => <a href={'https://youtu.be/' + id}>📼</a>)}</span> : '',
      },
    ], []);

  const tableInstance = useTable({
      columns,
      data,
      // don't do subcomponent https://github.com/tannerlinsley/react-table/pull/2531 but generator function:
      // https://react-table.tanstack.com/docs/api/useTable#row-properties
      // https://reactjs.org/docs/hooks-reference.html
      initialState: {
        hiddenColumns: ['iso'],
        sortBy: [
          { id: 'nparts', desc: true },
          { id: 'perimeter', desc: true },
          { id: 'holes', desc: true },
          { id: 'videos', desc: true },
          { id: 'name' },
        ]
      },
//      isMultiSortEvent: () => true,
//      disableSortRemove: true,
      defaultCanSort: true, // to allow sorting by aggregated 'nparts'
      aggregations: { first: (leaves, agg) => leaves[0] }
    }, useSortBy, useExpanded);

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
    const newSortBy = [...sortBy];
    newSortBy.sort((a, b) => a.id === designatedColumn.id ? -1 : b.id === designatedColumn.id ? 1 : 0);
    if (designatedColumn.sortedIndex === 0) {
      newSortBy[0].desc = !newSortBy[0].desc;
    }
    setSortBy(newSortBy);
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
       rows.map((row, r) => {
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
                      {i === 0 ? (
                        row.subRows.length > 0 ? 
                        // If it's a grouped cell, add an expander
                        <>
                          <span {...row.getToggleRowExpandedProps({ onClick: () => getCountry(row) })}>
                            { row.isExpanded ? '▾' : '▸'}{' '}{cell.render('Cell')}
                          </span>
                        </>
                        : <span style={{ paddingLeft: '2em' }}>Part {r}:{cell.render('Cell')}</span>) 
                      : cell.isPlaceholder ? null : ( // For cells with repeated values, render null
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
